# ČBF ICAL
ČBF ICAL was created to export your teams basketball matches into [icalendar](https://icalendar.org/)
format for you to import into your personal calendar
(like [Google Calendar](https://support.google.com/calendar/answer/37118), [Outlook](https://support.microsoft.com/en-us/office/import-calendars-into-outlook-8e8364e1-400e-4c0f-a573-fe76b5a2d379) etc.)
The idea is for this to be hosted on some server and for users to add this calendar by URL, allowing the calendar to refresh<sup>1</sup>.\
This project is written in `python 3` and for the HTTP interface `Flask` is used. The data is read from [ČBF](https://cbf.cz.basketball/xml-exporty/p58)

<sup>1</sup> From what I found Google Calendar updates approximately once 12-24 hours.

## Usage
This app provides two main routes:\
* `/cbf/find_team` with params `year` and `name`, returning phase ids and team ids of specific team for given year.
Right now only (case-insensitive) exact match is used. This can also take a lot of time,
so you might need to set higher timeout limit on your server.

* `/cbf/ical/<phase_id>/<team_id>` returning the icalendar with match schedule itself. This is two optional arguments -
`use-emoji` defining whether a basketball emoji (🏀) is used in the event name <sup>2</sup> (default is true), and `calendar-name` for specifying
calendar name put inside the icalendar (defualt is 'ČBF - rozpis zápasů').

<sup>2</sup> For `use-emoji` `f`, `false`, `0`, `t`, `true` and `1` can be used.

## How to set up on your own server
Right now the intended way is using [mod_wsgi](https://modwsgi.readthedocs.io/en/master/) (or any other wsgi server)
on your own server where you have terminal access.
First you should install all the requirements for `python 3` from `requirements.txt`
(for example by running `pip install -r requirements.txt`)

## TODO
Not everything is implemented perfectly and there is a lot of room for improvement. Here are some possible improvement:
* Create some HTML site that can be used to obtain link for specific schedule.
* Use some DB to store/cache some information, as finding where given team plays take quite some time.
* Better searching for a team by name (only substring can be supplied to match).
* Add calendar generation for referees.
* Create docker image for this, so it can be easily deployed.