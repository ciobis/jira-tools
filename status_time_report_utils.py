from datetime import datetime

def collect_state_transitions(changelog):
    result = []

    for history_log in changelog['histories']:
        status_change = _find_status_item(history_log)
        if not status_change:
            continue

        result.append({
            'event_time': history_log['created'],
            'from_status': status_change['fromString'],
            'to_status': status_change['toString']
        })

    return result
        

def _find_status_item(log):
    for item in log['items']:
        if item['field'] == 'status':
            return item
        
    return None


def calculate_status_times(issue, transitions):
    result = []
    if not transitions:
        return result
    
    last_time = issue['fields']['created']
    for tr in transitions:
        result.append({
            'status': tr['from_status'],
            'from_time': last_time,
            'to_time': tr['event_time'],
            'duration_minutes': _minutes_between(last_time, tr['event_time'])
        })

        last_time = tr['event_time']

    last_transition = transitions[-1]
    now = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f+0000')
    result.append({
        'status': last_transition['to_status'],
        'from_time': last_time,
        'to_time': now,
        'duration_minutes': _minutes_between(last_time, now)
    })

    return result

def _minutes_between(start_date_str, end_date_str):
    last_time_date = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M:%S.%f%z')
    event_time_date = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M:%S.%f%z')
    time_difference = event_time_date - last_time_date
    minutes = time_difference.total_seconds() / 60
    return round(minutes)

def get_issue_complete_time(issue, status_times, complete_status_name):
    if issue['fields']['status']['name'] != complete_status_name:
        return None
    
    for s in status_times:
        if s['status'] == complete_status_name:
            return s['from_time']
        
    return None