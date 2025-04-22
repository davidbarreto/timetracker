import argparse
import os
from tracker import Tracker

def main():

    parser = argparse.ArgumentParser(
        description='''Program for tracking time spent on specific issues.
        Note: A configuration file named 'tracker.conf' is required for proper execution. The file should contain the following settings:

        user               = ****            (mandatory)
        password           = ****            (mandatory)
        tracking.url       = URL             (mandatory)
        auth.url           = URL             (mandatory)
        default.start.time = HH:MM           (If not provided, user must provide it in tool arguments)
        default.end.time   = HH:MM           (If not provided, user must provide it in tool arguments)
        default-issue-id   = ISSUE_ID        (If not provided, user must provide it in tool arguments)
        ignore-weekends    = [true/false]    (May be ommited. Default value: true)
        log-level          = [INFO/DEBUG]    (May be ommited. Default value: INFO)

        Common Examples of Usage:
        - tracktime: Track time for today using default start and end times.
        - tracktime --wholeWeek: Track time for all days of the current week, from Sunday until Saturday. Note that if --includeWeekends is false (default), it will only track from Monday to Friday.
        - tracktime --wholeWeek --includeWeekends: Track time for the entire current week, including weekends.
        - tracktime 10/14[08:00-16:00] --exceptDates 13: Track time from the 10th to the 14th of the current month, between 08:00 and 16:00, excluding the 13th (for example, if it's a holiday).
        - tracktime --dates 2024-03-01[09:00-12:00] --log-level DEBUG: Track time on March 1st, 2024, from 09:00 to 12:00. Will register DEBUG messages in the console.
        - tracktime --dates 2024-02-15/2024-02-28 --includeWeekends: Track time between February 15th and February 28th, 2024, including weekends, and using default start and end times.
        - tracktime --generateConf: Generate a template configuration file named 'tracker.conf'. Useful for the first usage of the tool.
        ''',
        formatter_class=CustomFormatter
    )

    parser.add_argument('-d', '--dates', type=str, default='', help='''
        Specify the dates for tracking time. 
        Dates should be in the format YYYY-MM-DD, and times in the format HH:MM.
        You can define date ranges and time intervals within square brackets. 
        Use slashes to separate start and end dates (inclusive). 
        Examples:
        - '2024-02-26/2024-03-01[10:00-18:00]' - Track time between 2024-02-26 and 2024-03-01 (inclusive), from 10:00 to 18:00.
        - '02-26/03-01' - Track time between February 26th and March 1st of the current year.
        - '17/23' - Track time between the 17th and 23rd of the current month.
        If no year, month, or day is provided, the current year, month, or day will be used respectively.
        If no time is provided, default start and end times will be used (as per config file).
        If the config file doesn't provide any default start and end times, time must be provided.
    ''')

    parser.add_argument('-i', '--issueId', type=str, help='Specify the issue ID where you want to track time. Mandatory if not provided any default issue ID in the config file')
    parser.add_argument('--exceptDates', type=str, help='Specify dates that need to be excluded.')
    parser.add_argument('--wholeWeek', action='store_true', help='Track time for the entire week to which the specified date belongs, if enabled.')
    parser.add_argument('--includeWeekends', action='store_true', help='Include weekends in the tracking if enabled.')
    parser.add_argument('--logLevel', type=str, default='INFO', help='Specify the desired log level for console output during execution. Default value: INFO.')
    parser.add_argument('--generateConf', action='store_true', help='Generate a template configuration file named \'tracker.conf\'. Useful for the first usage of the tool')

    args = parser.parse_args()

    if args.generateConf:
        Tracker.generateTemplateConfFile()
    else:
        obj = Tracker.fromConfigFile()
        obj.execute(dates=args.dates, exceptDates=args.exceptDates, isWholeWeek=args.wholeWeek, issueId=args.issueId, logLevel=args.logLevel)

class CustomFormatter(argparse.RawTextHelpFormatter):
    def _split_lines(self, text, width):
        if text.startswith('R|'):
            return text[2:].splitlines()
        return argparse.RawTextHelpFormatter._split_lines(self, text, width) 

if __name__ == '__main__':
    main()

    


    