#!/usr/bin/env python3

import distutils.util
from datetime import datetime, timedelta
from flask import Flask, Response, request, url_for, redirect, render_template
import icalendar
import Cbf

app = Flask(__name__)


@app.route('/cbf/ical/<int:phase_id>/<int:team_id>')
@app.route('/cbf/ical/<int:phase_id>/<int:team_id>.ics')
def get_matches(phase_id: int, team_id: int):
    use_emoji = request.args.get(
        'use-emoji', True, type=distutils.util.strtobool)
    calendar_name = request.args.get('calendar-name', 'ČBF - rozpis zápasů')
    calendar = icalendar.Calendar()
    calendar['version'] = '2.0'
    calendar['prodid'] = '-//CBF//NONSGML//EN'
    calendar.add('X-WR-CALNAME', calendar_name)
    fetcher = Cbf.CbfApiFetcher_v1(Cbf.cbf_api_endpoint)
    schedule = fetcher.fetch_schedule(phase_id)
    if not schedule:
        return ''
    for match in schedule.matches:
        if match.home_team.id == team_id or match.visiting_team.id == team_id:
            event = icalendar.Event()
            event['uid'] = str(match.id)
            event.add('dtstart', match.start)
            event.add('duration', timedelta(hours=1, minutes=30))
            event.add('dtstamp', datetime.utcnow())
            if match.home_team.id == team_id:
                # home match
                summary = "vs. " + match.visiting_team.abbr
            else:
                # away/road game
                summary = " @  " + match.home_team.abbr
            event.add('summary', ('🏀' + ' ' if use_emoji else '') + summary)
            event.add('location', match.location.place +
                      ', ' + match.location.city)
            description = match.home_team.name + ' vs. ' + match.visiting_team.name
            if match.result and match.result.score != (0, 0):
                description += ' (' + str(match.result.score[0]) + ':' + str(
                    match.result.score[1]) + ')'
            event.add('description', description)
            calendar.add_component(event)
    r = Response(response=calendar.to_ical(), status=200,
                 content_type='text/calendar; charset=utf-8')
    return r


@app.route('/cbf/ical/v2/<int:phase_id>/<int:team_id>')
@app.route('/cbf/ical/v2/<int:phase_id>/<int:team_id>.ics')
def get_matches_v2(phase_id: int, team_id: int):
    use_emoji = request.args.get(
        'use-emoji', True, type=distutils.util.strtobool)
    calendar_name = request.args.get('calendar-name', 'ČBF - rozpis zápasů')
    calendar = icalendar.Calendar()
    calendar['version'] = '2.0'
    calendar['prodid'] = '-//CBF//NONSGML//EN'
    calendar.add('X-WR-CALNAME', calendar_name)
    fetcher = Cbf.CbfApiFetcher_v2()
    matches = fetcher.fetch_team_schedule_for_competition(team_id, phase_id)
    if not matches:
        return ''
    for match in matches:
        event = icalendar.Event()
        event['uid'] = str(match.id)
        event.add('dtstart', match.start)
        event.add('duration', timedelta(hours=1, minutes=30))
        event.add('dtstamp', datetime.utcnow())
        if match.home_team.id == team_id:
            # home match
            summary = "vs. " + match.visiting_team.abbr
        else:
            # away/road game
            summary = " @  " + match.home_team.abbr
        event.add('summary', ('🏀' + ' ' if use_emoji else '') + summary)
        location = match.location.place + ', ' + match.location.city
        if (match.location.coordinates is not None):
            event.add('geo',
                      (match.location.coordinates[0], match.location.coordinates[1]))
            event.add(
                "X-APPLE-STRUCTURED-LOCATION",
                f"geo:{match.location.coordinates[0]},{
                    match.location.coordinates[1]}",
                parameters={
                    "VALUE": "URI",
                    "X-ADDRESS": location,
                }
            )
        event.add('location', location)
        description = match.home_team.name + ' vs. ' + match.visiting_team.name
        if match.result and match.result.score != (0, 0):
            description += ' (' + str(match.result.score[0]) + ':' + str(
                match.result.score[1]) + ')'
        event.add('description', description)
        calendar.add_component(event)
    r = Response(response=calendar.to_ical(), status=200,
                 content_type='text/calendar; charset=utf-8')
    return r


@app.route('/cbf/find_team')
def find_team():
    year: int = request.args.get('year', type=int)
    team_name: str = request.args.get('name')
    return str(Cbf.find_team(year, team_name))


@app.route('/favicon.ico')
def favicon():
    return redirect(url_for('static', filename='favicon.ico'))


@app.route('/team-finder')
def team_finder():
    return render_template(
        'team_finder.html',
        areas=Cbf.areas,
        seasons=Cbf.fetch_season_list()
    )


if __name__ == '__main__':
    app.run(host="0.0.0.0")
