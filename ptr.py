#!/bin/env python3

import logging
import argparse
import getpass
import pprint
import datetime

# Local Dependencies
import time_reporter
import pyexch


def process_args():
    desc = { 'description': 'SEOAA Positive Time Reporting tool.',
             'epilog': '''Set environment variable PYEXCH_REGEX 
                          to control matching of Exchange events. 
                          Regex matching is always case-insensitive. 
                          Default value is PYEXCH_REGEX={}
                       '''.format( pyexch.PyExch.DEFAULT_REGEX )
           }
    parser = argparse.ArgumentParser( **desc )
    parser.add_argument( '--user', help='Username' )
    parser.add_argument( '--pwdfile',
        help='Plain text passwd ***WARNING: for testing only***' )
    parser.add_argument( '--passwd', help=argparse.SUPPRESS )
    parser.add_argument( '-n', '--dryrun', action='store_true' )
    parser.add_argument( '-q', '--quiet', action='store_true' )
    parser.add_argument( '-d', '--debug', action='store_true' )
    parser.add_argument( '-o', '--once', action='store_true',
        help='Submit only one week, then exit.' )
    action = parser.add_mutually_exclusive_group( required=True )
    action.add_argument( '--csv',
        help='Format: date,M,T,W,R,F (empty col means 8-hours worked that day)' )
    action.add_argument( '--exch', action='store_true',
        help='Load data from Exchange' )
    action.add_argument( '--list-overdue', action='store_true',
        help='List overdue dates and exit' )
    defaults = { 'user': None,
                 'pwdfile': None,
                 'passwd': None,
    }
    parser.set_defaults( **defaults )
    args = parser.parse_args()
    # check user
    if not args.user:
        args.user = getpass.getuser()
        logging.info( 'No user specified. Using "{0}".'.format( args.user ) )
    if args.pwdfile:
        # get passwd from file
        with open( args.pwdfile, 'r' ) as f:
            for l in f:
                args.passwd = l.rstrip()
                break
    else:
        # prompt user for passwd
        prompt = "Enter passwd for '{0}':".format( args.user )
        args.passwd = getpass.getpass( prompt )
#    # if no action specified, list-overdue dates
#    if not args.csv or not args.exch :
#        args.list_overdue = True
    return args


def process_csv( infile ):
    ''' Process csv file as rows with format DATE,M,T,W,R,F
        Such that values for work days are hours worked for that day
        and empty work day columns imply 8-hours (full-day)
        Returns a dict where key=date and val=list of weekday hours
    '''
    dates_hours = {}
    with open( infile, 'r' ) as f:
        for l in f:
            line = l.rstrip()
            logging.debug( "Processing line: '{0}'".format( line ) )
            parts = line.split( ',' )
            if len( parts ) != 6:
                logging.warn( "expecting 6 parts, got {0}".format( len(parts) ) )
                continue
            try:
                d = datetime.datetime.strptime( 
                    parts[0], 
                    time_reporter.Time_Reporter.DATE_FORMAT )
            except ( ValueError ) as e:
                logging.warn( "malformed date, skipping record" )
                continue
            if d.weekday() != 6:
                logging.warn( "date is not a Sunday, skipping record" )
                continue
            weekday_hours = [ 8 if len(x)<1 else int(x) for x in parts[1:6] ]
            if len( weekday_hours ) != 5:
                logging.warn( "expected 5 workdays, got {0}".format( len( weekday_hours ) ) )
                continue
            dates_hours[ d ] =  weekday_hours
    return dates_hours


def run( args ):
    data = {}
    reporter = time_reporter.Time_Reporter( username=args.user, password=args.passwd )
    overdue = reporter.get_overdue_weeks()
    if len( overdue ) < 1:
        raise SystemExit( "You have no overdue weeks. Congratulations!" )
    if args.list_overdue:
        print( "Overdue Dates" )
        for k in sorted( overdue.keys() ):
            print( k.strftime( '%Y-%b-%d' ) )
        raise SystemExit()
    if args.csv:
        data = process_csv( args.csv )
        logging.debug( 'CSV data: {0}'.format( pprint.pformat( data ) ) )
    elif args.exch:
        pyex = pyexch.PyExch( pwd=args.passwd )
        start_date = min( overdue.keys() )
        data = pyex.weekly_hours_worked( datetime.datetime.combine( start_date, datetime.time() ) )
    # Walk through list of overdue dates
    for key in sorted( overdue ):
        logging.info( 'Overdue date: {0}'.format( key ) )
        if key in data:
            logging.info( 'Found match: KEY:{0} VAL:{1}'.format( key, data[ key ] ) )
            if not args.dryrun:
                reporter.submit( date=key, hours=data[ key ] )
                logging.info( 'Successfully submitted week:{0} hours:{1}'.format( key, data[ key ] ) )
            if args.once:
                raise SystemExit()
        

if __name__ == '__main__':
    logging.basicConfig( level=logging.INFO )
#    for key in logging.Logger.manager.loggerDict:
#        print(key)
    for key in [ 'weblib', 'selection', 'grab', 'time_reporter', 'requests', 'ntlm_auth', 'exchangelib', 'future_stdlib' ] :
        logging.getLogger(key).setLevel(logging.CRITICAL)
    args = process_args()
    if args.debug:
        logging.getLogger().setLevel( logging.DEBUG )
    elif args.quiet:
        logging.getLogger().setLevel( logging.WARNING )
    run( args )
