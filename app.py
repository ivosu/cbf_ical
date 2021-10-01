#!/usr/bin/env python3

import distutils.util
from flask import Flask, request
from typing import List, Tuple
import icalendar
import Cbf

app = Flask(__name__)


@app.route('/cbf/ical/<int:phase_id>/<int:team_id>')
def get_matches(phase_id: int, team_id: int):
    use_emoji = request.args.get('use-emoji', True, type=distutils.util.strtobool)
    calendar_name = request.args.get('calendar-name', 'ČBF - rozpis zápasů')
    calendar = icalendar.Calendar()
    calendar['version'] = '2.0'
    calendar['prodid'] = '-//CBF//NONSGML//EN'
    calendar.add('X-WR-CALNAME', calendar_name)
    for match in Cbf.Schedule.fetch_from_cbf(phase_id).matches:
        if match.home_team.id == team_id or match.visiting_team.id == team_id:
            event = icalendar.Event()
            event['uid'] = str(match.id)
            event.add('dtstart', match.start)
            if match.home_team.id == team_id:
                # home match
                summary = "vs. " + match.visiting_team.abbr
            else:
                # away/road game
                summary = " @  " + match.home_team.abbr
            event.add('summary', ('🏀' + ' ' if use_emoji else '') + summary)
            event.add('location', match.place + ', ' + match.city)
            description = match.home_team.name + ' vs. ' + match.visiting_team.name
            if match.result and match.result.score != (0, 0):
                description += ' (' + str(match.result.score[0]) + ':' + str(match.result.score[1]) + ')'
            event.add('description', description)
            calendar.add_component(event)
    return calendar.to_ical()


@app.route('/cbf/find_team/<int:year>/<string:team_name>')
def find_team(year: int, team_name: str):
    lower_team_name = team_name.lower()
    team_id_and_phases: List[Tuple[int, int]] = []
    for division in Cbf.Season.fetch_from_cbf(year).divisions:
        for phase in division.phases:
            for team_standing in phase.standings.team_standings:
                if team_standing.name.lower() == lower_team_name:
                    team_id_and_phases.append((phase.id, team_standing.id))
    return str(team_id_and_phases)


if __name__ == '__main__':
    app.run(host="0.0.0.0")
