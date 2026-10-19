"""DynamoDB persistence for synthetic ClinicAI demonstration data."""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError
from config import REGION, PREFIX

_db = boto3.resource('dynamodb', region_name=REGION)
_KEYS = {'Patients': 'patient_id', 'Consultations': 'consultation_id', 'Appointments': 'appointment_id'}

def _table(kind):
    if kind not in _KEYS:
        raise ValueError(f'Unsupported collection: {kind}')
    return _db.Table(f'{PREFIX}{kind}')

def _now():
    return datetime.now(timezone.utc).isoformat()

def _ddb(value):
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {str(k): _ddb(v) for k,v in value.items()}
    if isinstance(value, list):
        return [_ddb(v) for v in value]
    return value

def setup_tables():
    client = boto3.client('dynamodb', region_name=REGION)
    existing = set(client.list_tables().get('TableNames', []))
    for kind, key in _KEYS.items():
        name = f'{PREFIX}{kind}'
        if name not in existing:
            client.create_table(TableName=name, KeySchema=[{'AttributeName': key, 'KeyType': 'HASH'}], AttributeDefinitions=[{'AttributeName': key, 'AttributeType': 'S'}], BillingMode='PAY_PER_REQUEST')
        client.get_waiter('table_exists').wait(TableName=name)

def get(kind, identifier):
    if not identifier:
        return None
    return _table(kind).get_item(Key={_KEYS[kind]: identifier}).get('Item')

def list_items(kind, limit=500):
    table = _table(kind)
    items = []
    kwargs = {'Limit': min(100, limit)}
    while len(items) < limit:
        result = table.scan(**kwargs)
        items.extend(result.get('Items', []))
        if not result.get('LastEvaluatedKey'):
            break
        kwargs['ExclusiveStartKey'] = result['LastEvaluatedKey']
    return items[:limit]

def create_patient(name, age=None, dob=None, insurance_company=None, insurance_member_id=None, phone=None, email=None):
    if not str(name).strip():
        raise ValueError('Patient name is required')
    patient = {'patient_id': 'P-' + uuid.uuid4().hex[:12], 'name': name.strip(), 'age': age, 'created_at': _now()}
    patient.update({k:v for k,v in {'dob': dob, 'insurance_company': insurance_company, 'insurance_member_id': insurance_member_id, 'phone': phone, 'email': email}.items() if v})
    _table('Patients').put_item(Item=_ddb(patient), ConditionExpression='attribute_not_exists(patient_id)')
    return patient

def update_patient(patient_id, name, age=None):
    if not str(name).strip():
        raise ValueError('Patient name is required')
    response = _table('Patients').update_item(Key={'patient_id': patient_id}, UpdateExpression='SET #n=:n, age=:a, updated_at=:t', ExpressionAttributeNames={'#n': 'name'}, ExpressionAttributeValues={':n': name.strip(), ':a': age, ':t': _now()}, ConditionExpression='attribute_exists(patient_id)', ReturnValues='ALL_NEW')
    return response['Attributes']

def save_consultation(patient_id, extracted, transcript, approved_by):
    if not get('Patients', patient_id):
        raise ValueError('Patient not found')
    item = {'consultation_id': 'C-' + uuid.uuid4().hex[:12], 'patient_id': patient_id, 'extracted': _ddb(extracted), 'transcript': transcript, 'approved_by': approved_by, 'created_at': _now()}
    _table('Consultations').put_item(Item=item, ConditionExpression='attribute_not_exists(consultation_id)')
    return item

def update_consultation(consultation_id, extracted, approved_by):
    response = _table('Consultations').update_item(Key={'consultation_id': consultation_id}, UpdateExpression='SET extracted=:e, approved_by=:a, updated_at=:t', ExpressionAttributeValues={':e': _ddb(extracted), ':a': approved_by, ':t': _now()}, ConditionExpression='attribute_exists(consultation_id)', ReturnValues='ALL_NEW')
    return response['Attributes']

def book_appointment(patient_id, appointment_at, clinician, approved_by, reason='Follow-up'):
    """Atomically reserve a clinician/time pair; no fabricated availability."""
    if not get('Patients', patient_id):
        raise ValueError('Patient not found')
    if not clinician.strip():
        raise ValueError('Choose a clinician')
    try:
        dt = datetime.fromisoformat(appointment_at)
    except ValueError as exc:
        raise ValueError('Invalid appointment date/time') from exc
    if dt.tzinfo is None:
        raise ValueError('Appointment time must include a timezone offset')
    if dt.astimezone(timezone.utc) <= datetime.now(timezone.utc):
        raise ValueError('Appointment must be in the future')
    # One item per clinician and exact instant: DynamoDB conditional put prevents two bookings.
    key = 'SLOT#' + clinician.strip().casefold() + '#' + dt.astimezone(timezone.utc).isoformat()
    item = {'appointment_id': key, 'patient_id': patient_id, 'appointment_at': appointment_at, 'clinician': clinician.strip(), 'reason': reason, 'approved_by': approved_by, 'status': 'Booked', 'created_at': _now()}
    try:
        _table('Appointments').put_item(Item=item, ConditionExpression='attribute_not_exists(appointment_id)')
    except ClientError as exc:
        if exc.response.get('Error', {}).get('Code') == 'ConditionalCheckFailedException':
            raise ValueError('This clinician already has a booking at that time') from exc
        raise
    return item


def update_patient_details(patient_id, **details):
    allowed = {'dob', 'insurance_company', 'insurance_member_id', 'phone', 'email', 'address', 'allergies', 'medical_history'}
    fields = {k: v for k, v in details.items() if k in allowed and v is not None and v != ''}
    if not fields:
        return get('Patients', patient_id)
    fields['updated_at'] = _now()
    names = {f'#f{i}': key for i, key in enumerate(fields)}
    values = {f':v{i}': _ddb(value) for i, value in enumerate(fields.values())}
    expression = 'SET ' + ', '.join(f'{n}={v}' for n, v in zip(names, values))
    return _table('Patients').update_item(
        Key={'patient_id': patient_id}, UpdateExpression=expression,
        ExpressionAttributeNames=names, ExpressionAttributeValues=values,
        ConditionExpression='attribute_exists(patient_id)', ReturnValues='ALL_NEW'
    )['Attributes']


def search_patients(name, dob):
    """Exact normalized name AND DOB; legacy records without DOB cannot match."""
    from datetime import date
    if not name.strip() or not dob.strip():
        raise ValueError('Patient name and date of birth are required')
    dob = date.fromisoformat(dob.strip()).isoformat()
    wanted = ' '.join(name.casefold().split())
    # Scan is appropriate for small demo tables; use indexed keys for production.
    table = _table('Patients')
    results = []
    kwargs = {'FilterExpression': Attr('dob').eq(dob)}
    while True:
        page = table.scan(**kwargs)
        results.extend(p for p in page.get('Items', []) if ' '.join(str(p.get('name', '')).casefold().split()) == wanted)
        if 'LastEvaluatedKey' not in page:
            break
        kwargs['ExclusiveStartKey'] = page['LastEvaluatedKey']
    return results


def search_patients_by_name(name):
    """Case-insensitive partial name matching for demo records.

    Returns every matching patient so staff can verify DOB before opening a chart.
    """
    query = ' '.join(name.casefold().split())
    if not query:
        raise ValueError('Enter at least part of a patient name')
    table = _table('Patients')
    results = []
    kwargs = {}
    while True:
        page = table.scan(**kwargs)
        for patient in page.get('Items', []):
            normalized = ' '.join(str(patient.get('name', '')).casefold().split())
            if query in normalized:
                results.append(patient)
        if 'LastEvaluatedKey' not in page:
            break
        kwargs['ExclusiveStartKey'] = page['LastEvaluatedKey']
    return sorted(results, key=lambda p: (str(p.get('name','')).casefold(), str(p.get('dob',''))))


def records_for_patient(patient_id):
    return {
        kind: sorted((i for i in list_items(kind, limit=10000) if i.get('patient_id') == patient_id),
                     key=lambda i: i.get('created_at', ''), reverse=True)
        for kind in ('Consultations', 'Appointments')
    }


def reschedule_appointment(appointment_id, patient_id, appointment_at, reason):
    """Atomically move a confirmed booking, preventing exact-slot collisions."""
    from boto3.dynamodb.types import TypeSerializer
    original = get('Appointments', appointment_id)
    if not original or original.get('patient_id') != patient_id:
        raise ValueError('Appointment not found for this patient')
    if str(original.get('status', '')).lower() not in ('booked', 'confirmed', 'scheduled'):
        raise ValueError('Only confirmed appointments can be edited')
    try:
        new_dt = datetime.fromisoformat(appointment_at)
    except ValueError as exc:
        raise ValueError('Invalid appointment date or time') from exc
    if new_dt.tzinfo is None:
        raise ValueError('Appointment time must include a timezone')
    if new_dt.astimezone(timezone.utc) <= datetime.now(timezone.utc):
        raise ValueError('Select a future appointment time')
    clinician = original['clinician']
    new_id = 'SLOT#' + clinician.strip().casefold() + '#' + new_dt.astimezone(timezone.utc).isoformat()
    table = _table('Appointments')
    if new_id == appointment_id:
        return table.update_item(
            Key={'appointment_id': appointment_id},
            UpdateExpression='SET reason=:r, updated_at=:t',
            ConditionExpression='attribute_exists(appointment_id) AND patient_id=:p',
            ExpressionAttributeValues={':r': reason or 'Follow-up', ':t': _now(), ':p': patient_id},
            ReturnValues='ALL_NEW',
        )['Attributes']
    item = dict(original)
    item.update({'appointment_id': new_id, 'appointment_at': appointment_at, 'reason': reason or 'Follow-up', 'updated_at': _now()})
    serializer = TypeSerializer()
    encode = lambda obj: {k: serializer.serialize(v) for k, v in obj.items()}
    try:
        boto3.client('dynamodb', region_name=REGION).transact_write_items(TransactItems=[
            {'Put': {'TableName': table.name, 'Item': encode(item), 'ConditionExpression': 'attribute_not_exists(appointment_id)'}},
            {'Delete': {'TableName': table.name, 'Key': encode({'appointment_id': appointment_id}),
                        'ConditionExpression': 'attribute_exists(appointment_id) AND patient_id = :pid',
                        'ExpressionAttributeValues': {':pid': serializer.serialize(patient_id)}}}
        ])
    except ClientError as exc:
        if exc.response.get('Error', {}).get('Code') in ('TransactionCanceledException', 'ConditionalCheckFailedException'):
            raise ValueError('Unable to move the appointment. The requested slot may already be booked; refresh and try another time.') from exc
        raise
    return item
