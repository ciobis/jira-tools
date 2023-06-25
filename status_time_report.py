import yaml
from atlassian import Jira
from simple_term_menu import TerminalMenu
import pandas as pd

from status_time_report_utils import collect_state_transitions
from status_time_report_utils import calculate_status_times
from status_time_report_utils import get_issue_complete_time

def generate_xlsx(jira_config, report_config):
    jira = Jira(url=jira_config['url'], token=jira_config['token'])
    
    board_names = map(lambda x: x['name'], report_config['boards'])
    terminal_menu = TerminalMenu(board_names, title='Select board')
    board_idx = terminal_menu.show()
    selected_board = report_config['boards'][board_idx]

    print(f'Fetching sprints for board: {selected_board["name"]}')
    active_sprints = jira.get_all_sprint(selected_board['id'], 'active')['values']
    inactive_sprints = jira.get_all_sprint(selected_board['id'])['values']
    inactive_sprints = sorted(inactive_sprints, key= lambda s : s.get('startDate', '2099-01-01'), reverse=True)
    inactive_sprints = inactive_sprints[0:5]
    sprints = active_sprints + inactive_sprints

    sprint_names = map(lambda x: f"{x['name']} ({x['state']})", sprints)
    terminal_menu = TerminalMenu(sprint_names, title='Select sprint')
    sprint_idx = terminal_menu.show()
    selected_sprint = sprints[sprint_idx]

    print(f'Fetching issues for sprint: {selected_sprint["name"]}')
    sprint_issues = jira.get_sprint_issues(selected_sprint['id'], 0, 100)['issues']
    result_rows = []
    for issue in sprint_issues:
        issue_key = issue['key']
        print(f'Fetching changelog for issue {issue_key}')
        change_log = jira.get_issue_changelog(issue_key)
        state_transitions = collect_state_transitions(change_log)
        status_times = calculate_status_times(issue, state_transitions)
        complete_time = get_issue_complete_time(issue, status_times, report_config['completed_status_name'])

        for status in status_times:
            issue_fields = issue['fields']

            sprint = issue_fields.get('sprint', {}).get('name', '')
            if not sprint and issue_fields.get('closedSprints', []):
                closed_sprints = issue_fields.get('closedSprints', [])
                closed_sprints = sorted(closed_sprints, key= lambda s : s.get('startDate', '2000-01-01'), reverse=True)                
                sprint = closed_sprints[0].get('name', '')

            status['issue_type'] = issue_fields['issuetype']['name']
            status['issue_key'] = issue_key
            status['priority'] = issue_fields['priority']['name']
            status['date_created'] = issue_fields['created']
            status['date_resolved'] = complete_time
            status['current_status'] = issue_fields['status']['name']
            status['sprint'] = sprint

            result_rows.append(status)

    df = pd.DataFrame.from_records(result_rows)
    df = df.assign(duration_hours = df.duration_minutes / 60)
    df = df.assign(duration_days = df.duration_minutes / 1440)
    df = df.round({'duration_hours': 2, 'duration_days': 2})

    for output in report_config['output']:
        type = output['type']
        if type == 'raw':
            file_name = output['file_name']
            output_df = df.rename(columns=report_config['columns']['translate'])
            output_df.to_excel(file_name)

            print(f'Report generated at: {file_name}')
        if type == 'pivot':
            file_name = output['file_name']
            output_df = df.pivot_table(index=output['rows'],
                   columns=[output['column']],
                   values=output['values'],
                   aggfunc='sum')
            
            if output['column_ordering']:
                output_df = output_df.reindex(output['column_ordering'], axis='columns', level=output['column'])
            
            output_df = output_df.rename(columns=report_config['columns']['translate'])
            output_df.to_excel(file_name)
            print(f'Report generated at: {file_name}')


config = None
with open('config.yaml', "r") as stream:
    config = yaml.safe_load(stream)

generate_xlsx(config['jira'], config['issue_status_time_report'])