import unittest
from tracker import Tracker

class JttTrackerTest(unittest.TestCase):

    def __init__(self):
        obj = Tracker('user', 'pass', 'https://test.com', "https://test.com", '09:00', '17:00', 'TASK')

    def test_SplitDateAndTime(self):
        
        date, time = self.obj.splitDateAndTime('2024-02-26/2024-03-01[10:00-18:00]')
        self.assertEqual(date, '2024-02-26/2024-03-01')
        self.assertEqual(time, '10:00-18:00')

        date, time = self.obj.splitDateAndTime('2024-02-26/2024-03-01')
        self.assertEqual(date, '2024-02-26/2024-03-01')
        self.assertEqual(time, '')

    def test_FormatIsoDateTime(self):

        self.assertEqual(self.obj.formatIsoDateTime('2024-02-26', '09:00'), '2024-02-26T09:00:00.000Z')

    def test_FormatTime(self):

        start, end = self.obj.formatTime('08:00-13:00')
        self.assertEqual(start, '08:00')
        self.assertEqual(end, '13:00')

        start, end = self.obj.formatTime('')
        self.assertEqual(start, self.obj.defaultStartTime)
        self.assertEqual(end, self.obj.defaultEndTime)

        with self.assertRaises(ValueError):
            self.obj.formatTime('09:00')

        with self.assertRaises(ValueError):
            self.obj.formatTime('09:00-10:00-11:00')

    def test_CompleteDate(self):

        date, _ = self.obj.buildDate('2020-11-30')
        self.assertEqual(date, '2020-11-30')
        
        date, _ = self.obj.buildDate('11-30')
        self.assertEqual(date, self.obj.defaultYear + '-11-30')
        
        date, _ = self.obj.buildDate('01')
        self.assertEqual(date, self.obj.defaultYear + '-' + self.obj.defaultMonth + '-01')

        date, _ = self.obj.buildDate('')
        self.assertEqual(date, self.obj.defaultYear + '-' + self.obj.defaultMonth + '-' + self.obj.defaultDay)

        with self.assertRaises(ValueError):
            self.obj.buildDate('123')

        with self.assertRaises(ValueError):
            self.obj.buildDate('yyyy-mm-dd')

        with self.assertRaises(ValueError):
            self.obj.buildDate('2024-22-22')

        with self.assertRaises(ValueError):
            self.obj.buildDate('2024-01-33')

        with self.assertRaises(ValueError):
            self.obj.buildDate('-2020-01-01')

    def test_HandleDateRanges(self):

        self.assertEqual(self.obj.handleDateRanges('2024-02-05/2024-02-09'), ['2024-02-05', '2024-02-06', '2024-02-07', '2024-02-08', '2024-02-09'])
        
        self.obj.isWeekendIgnored = True
        self.assertEqual(self.obj.handleDateRanges('2024-02-01/2024-02-05'), ['2024-02-01', '2024-02-02', '2024-02-05'])
        self.assertEqual(self.obj.handleDateRanges('2024-02-24/2024-02-25'), [])

        self.obj.isWeekendIgnored = False
        self.assertEqual(self.obj.handleDateRanges('2024-02-01/2024-02-05'), ['2024-02-01', '2024-02-02', '2024-02-03', '2024-02-04', '2024-02-05'])
        self.assertEqual(self.obj.handleDateRanges('2024-02-24/2024-02-25'), ['2024-02-24', '2024-02-25'])

        with self.assertRaises(ValueError):
            self.obj.handleDateRanges('2024-01-05/2024-01-01')

        with self.assertRaises(ValueError):
            self.obj.handleDateRanges('2024-01-01/2024-01-01')

    def test_RemoveExceptDates(self):

        list = self.obj.removeExceptDates(
            [self.obj.TrackInterval(start = '2020-01-01T20:30:00.00Z', end = '2020-01-02T18:00:00.00Z'), self.obj.TrackInterval(start = '2020-02-01T20:30:00.00Z', end = '2020-02-02T20:30:00.00Z')], 
            [self.obj.TrackInterval(start = '2020-01-01T20:30:00.00Z', end = '2020-01-02T18:00:00.00Z'), self.obj.TrackInterval(start = '2020-03-01T20:30:00.00Z', end = '2020-03-02T20:30:00.00Z')])
        
        self.assertEqual(list, [self.obj.TrackInterval(start = '2020-02-01T20:30:00.00Z', end = '2020-02-02T20:30:00.00Z')])

    def test_FilterCookies(self):

        cookies = self.obj.filterCookies('JSESSIONID=B401A2670D6B63765E60F722C04C5978; Path=/; HttpOnly;SameSite=None;  Secure, atlassian.xsrf.token=ATEB-JR6T-2WJL-PHO8_5e0b2aca9824b6bef3b4846cb106263f553c9484_lout; Path=/;SameSite=None;  Secure')
        self.assertEqual(cookies, 'JSESSIONID=B401A2670D6B63765E60F722C04C5978; atlassian.xsrf.token=ATEB-JR6T-2WJL-PHO8_5e0b2aca9824b6bef3b4846cb106263f553c9484_lout')

    def test_ParseWholeWeek(self):

        self.assertEqual(self.obj.parseWholeWeek('2024-02-01'), '2024-01-28/2024-02-03')
        self.assertEqual(self.obj.parseWholeWeek('2024-03-02'), '2024-02-25/2024-03-02')
        self.assertEqual(self.obj.parseWholeWeek('2024-06-24'), '2024-06-23/2024-06-29')
        self.assertEqual(self.obj.parseWholeWeek('2024-03-01[09:00-17:00]'), '2024-02-25/2024-03-02[09:00-17:00]')
        self.assertEqual(self.obj.parseWholeWeek('2024-01-01[09:00-17:00]'), '2023-12-31/2024-01-06[09:00-17:00]')

    def test_ParseSingleDateInstruction(self):
        parsedDate = self.obj.parseSingleDateInstruction('2020-11-30[09:00-13:00]')
        expected = [self.obj.TrackInterval('2020-11-30T09:00:00.000Z', '2020-11-30T13:00:00.000Z')]
        self.assertEqual(parsedDate, expected)
        parsedDate = self.obj.parseSingleDateInstruction('2020-11-30/2020-12-01[09:00-13:00]')
        expected = [self.obj.TrackInterval('2020-11-30T09:00:00.000Z', '2020-11-30T13:00:00.000Z'), self.obj.TrackInterval('2020-12-01T09:00:00.000Z', '2020-12-01T13:00:00.000Z')]
        self.assertEqual(parsedDate, expected)