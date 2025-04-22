from jproperties import Properties
import requests
import datetime
import re
import logging
from logging.handlers import TimedRotatingFileHandler
from dataclasses import dataclass

class Tracker:

    JSESSION_ID_KEY = 'JSESSIONID='
    ATLASSIAN_KEY = 'atlassian.xsrf.token='
    CONFIG_PATH='./tracker.conf'

    @dataclass
    class TrackInterval:
        start: str
        end: str

    def __init__(self, user, password, trackingUrl, authUrl, defaultStartTime, defaultEndTime, defaultIssueId, isWeekendIgnored = True, logLevel='INFO'):
        
        self.user = user
        self.password = password
        self.trackingUrl = trackingUrl
        self.authUrl = authUrl
        self.defaultStartTime = defaultStartTime
        self.defaultEndTime = defaultEndTime
        self.defaultIssueId = defaultIssueId
        self.isWeekendIgnored = isWeekendIgnored

        self.initDateFields()

        self.logging = logging.getLogger('tracker')
        fileHandler = TimedRotatingFileHandler(filename='tracker.log', when='W0', interval=1, backupCount=8)
        fileHandler.setLevel(logging.INFO)
        fileHandler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

        self.consoleHandler = logging.StreamHandler()
        self.consoleHandler.setLevel(logging.getLevelName(logLevel))

        self.logging.addHandler(fileHandler)
        self.logging.addHandler(self.consoleHandler)

        # Will accept and pass every message to the handlers
        # Let the handlers filter the messages they need
        self.logging.setLevel(1)

        self.logging.debug('Object constructed with params: ' +
                           'user [%s] password [%s] trackingUrl [%s] authUrl [%s] defaultStartTime [%s] defaultEndTime [%s] ' +
                           'defaultIssueId [%s] isWeekendIgnored [%s] logLevel [%s]',
                           user, password, trackingUrl, authUrl, defaultStartTime, defaultEndTime, defaultIssueId, isWeekendIgnored, logLevel)


    @classmethod
    def fromConfigFile(cls):
        configs = Properties()
        with open(cls.CONFIG_PATH, 'rb') as configFile:
            configs.load(configFile, 'utf-8')

        user = configs.get('user').data
        password = configs.get('password').data
        trackingUrl = configs.get('tracking.url').data
        authUrl = configs.get('auth.url').data
        defaultStartTime = configs.get('default.start.time').data
        defaultEndTime = configs.get('default.end.time').data
        defaultIssueId = configs.get('default-issue-id').data
        isWeekendIgnored = cls.toBool(configs.get('ignore-weekends').data)
        logLevel = configs.get('log-level').data

        return cls(user, password, trackingUrl, authUrl, defaultStartTime, defaultEndTime, defaultIssueId, isWeekendIgnored, logLevel)
    
    @classmethod
    def generateTemplateConfFile(cls):
        
        prop = Properties()

        prop['user'] = '****'
        prop['password'] = '****'
        prop['tracking.url'] = 'URL'
        prop['auth.url'] = 'URL'
        prop['default.start.time'] = '09:00'
        prop['default.end.time'] = '17:00'
        prop['default-issue-id'] = 'ISSUE_ID'
        prop['ignore-weekends'] = 'true'
        prop['log-level'] = 'INFO'

        # Write the properties to the configuration file
        with open(cls.CONFIG_PATH, 'wb') as configFile:
            prop.store(configFile, encoding="utf-8")
                   
    @classmethod
    def toBool(cls, booleanString):
        return booleanString.lower() in ['true']

    def initDateFields(self):

        today = datetime.date.today()
        self.defaultYear = str(today.year)
        self.defaultMonth = '{:02d}'.format(today.month)
        self.defaultDay = '{:02d}'.format(today.day)

    def parseDateInstruction(self, dateInstruction):
        
        result = []
        datesList = dateInstruction.split(',')
        for date in datesList:
            result.extend(self.parseSingleDateInstruction(date))

        return result

    # E.g.:
    # 2024-02-26/2024-03-01[10:00-18:00]
    # 02-26/03-01 -> Will default year to current one
    # 17/23 -> Will default year and month to current one
    def parseSingleDateInstruction(self, dateInstruction):

        dateInstruction = dateInstruction.strip()
        datePart, timePart = self.splitDateAndTime(dateInstruction)
        
        dates = self.formatDate(datePart)
        startTime, endTime = self.formatTime(timePart)

        result = []
        for date in dates:
            dateTarget = self.TrackInterval(start = self.formatIsoDateTime(date, startTime), end = self.formatIsoDateTime(date, endTime))
            result.append(dateTarget)

        return result
    
    def formatDate(self, date):

        if '/' in date:
            return self.handleDateRanges(date)
        else:
            formattedDate, _ = self.buildDate(date)
            return [formattedDate]
        
    def handleDateRanges(self, date):

        result = []
        dateInterval = date.split('/')
        
        startDateString, startDate = self.buildDate(dateInterval[0])
        endDateString, endDate = self.buildDate(dateInterval[1])

        if (startDate >= endDate):
            raise ValueError('Start date [{}] must be smaller than End date [{}]'.format(startDateString, endDateString))

        pointer = startDate
        while pointer <= endDate:
            if not self.ignoreDate(pointer):
                result.append(pointer.strftime('%Y-%m-%d'))
            pointer += datetime.timedelta(days=1)

        return result
    
    def ignoreDate(self, date):
        return self.isWeekendIgnored and date.weekday() >= 5
        
    def buildDate(self, date):

        date = date.strip()

        patternFull = r'^\d{4}-\d{2}-\d{2}$'
        patternMonthDay = r'^\d{2}-\d{2}$'
        patternDay = r'^\d{1,2}$'

        if date == '':
            finalDate = self.defaultYear + '-' + self.defaultMonth + '-' + self.defaultDay
        elif re.match(patternFull, date):
            finalDate = date
        elif re.match(patternMonthDay, date):
            finalDate = self.defaultYear + '-' + date
        elif re.match(patternDay, date):
            finalDate = self.defaultYear + '-' + self.defaultMonth + '-' + '{:02d}'.format(int(date))
        else:
            raise ValueError('Date ' + date + ' is in an invalid format')
          
        dateObject = datetime.datetime.strptime(finalDate, '%Y-%m-%d')

        self.logging.debug('Built date: ' + finalDate)

        return finalDate, dateObject
    
    def formatTime(self, timeInterval):

        if (timeInterval == ''):
            return self.defaultStartTime, self.defaultEndTime

        timeComponents = timeInterval.split('-')
        if len(timeComponents) != 2:
            raise ValueError('Time range must be informed inside brackets in the format [startTime-endTime]. Ex: [09:00-17:00]')
        
        return timeComponents[0], timeComponents[1]
    
    def formatIsoDateTime(self, date, time):
        return date + 'T' + time + ':00.000Z'
        
    def splitDateAndTime(self, datetime):

        start = datetime.find('[')
        if (start != -1):
            return datetime[:start], datetime[start+1:-1]
        else:
            return datetime, ''
        
    def removeExceptDates(self, dates, exceptDates):
        self.logging.debug('Removing except dates. Current dates: [%s]. Except dates [%s]', dates, exceptDates)

        return [x for x in dates if x not in exceptDates]
    
    def auth(self):

        body = {
            "password": self.password,
            "user": self.user
        }

        self.logging.debug('Authenticating to Tracker server. URL [%s] Body [%s]', self.authUrl, body)

        response = requests.post(url=self.authUrl, json=body)
        status = response.status_code

        self.logging.info('Got response from auth with status code [%d]', status)

        if status > 300:
            raise Exception(f'Failed to authenticate to server. Server returned status code: {status}')

        cookiesString = response.headers.get('Set-Cookie')
        return self.filterCookies(cookiesString)
    
    def filterCookies(self, cookieString):

        if cookieString in [None, '']:
            return ''

        cookieList = re.split(';|,', cookieString)
        return '; '.join(cookie.strip() for cookie in cookieList if self.JSESSION_ID_KEY in cookie or self.ATLASSIAN_KEY in cookie)
    
    # Find last sunday and next saturday from a specific date
    # and generate a date parameter like this: sunday/saturday[time]
    def parseWholeWeek(self, dates):

        if '/' in dates or ',' in dates:
            raise ValueError('You must provide just one date in -dates when use --isWholeWeek')
        
        dateComponents = dates.split('[')
        _, targetDate = self.buildDate(dateComponents[0])

        sunday = targetDate - datetime.timedelta(days=(targetDate.weekday()+1))
        saturday = sunday + datetime.timedelta(days=6)

        firstDay = sunday.strftime('%Y-%m-%d')
        lastDay = saturday.strftime('%Y-%m-%d')

        result = firstDay + '/' + lastDay
        if len(dateComponents) > 1:
            result += '[' + dateComponents[1]

        self.logging.info('Considering dates = ' + result)

        return result

    def execute(self, dates, exceptDates=None, isWholeWeek=False, issueId=None, logLevel=''):

        if logLevel != '':
            self.consoleHandler.setLevel(logging.getLevelName(logLevel))
        
        self.logging.info('Executing tracker')
        self.logging.debug('Parameters: dates [%s] exceptDates [%s] isWholeWeek [%s] IssueId [%s] logLevel [%s]',
                           dates, exceptDates, isWholeWeek, issueId, logLevel)

        if not self.isWeekendIgnored:
            self.logging.warning('Weekeends will not be ignored in this execution!')

        if not issueId:
            self.logging.debug('Using issueId as the default [%s]', self.defaultIssueId)
            issueId = self.defaultIssueId

        if isWholeWeek:
            dates = self.parseWholeWeek(dates)

        datesList = self.parseDateInstruction(dates)
            
        if exceptDates:
            exceptDatesList = self.parseDateInstruction(exceptDates)
            datesList = self.removeExceptDates(datesList, exceptDatesList)

        headers = {
            "Cookie": self.auth()
        }
        
        self.logging.debug('Sending [%d] tracking requests to server:', len(datesList))
        for date in datesList:
            body = {
                "comment": "",
                "endTime": date.end,
                "issueKey": issueId,
                "startTime": date.start
            }
            self.sendRequest(body, headers)
            
            
    def sendRequest(self, body, headers):
        self.logging.debug('URL: [%s] headers: [%s] body [%s]', self.trackingUrl, headers, body)
        self.logging.info('Sending request with body [%s]',  body)

        response = requests.post(self.trackingUrl, json=body, headers=headers)
        status = response.status_code

        self.logging.info('Got response with status code [%d] and body [%s]', status, response.json())

        if status > 300:
            raise Exception(f'One request failed with status code: {status}. Check what happened in Tracker server...')