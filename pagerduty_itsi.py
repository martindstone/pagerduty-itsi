import sys
import json
import urllib2
import time

from fnmatch import fnmatch

from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))

from ITOA.itoa_config import get_supported_objects
from ITOA.setup_logging import setup_logging
from itsi.event_management.sdk.eventing import Event
from itsi.event_management.sdk.custom_event_action_base import CustomEventActionBase


def send_notification(payload, logger):
	settings = payload.get('configuration')
	logger.info("Sending incident with settings %s" % settings)

	url = settings.get('integration_url_override')
	token = settings.get('token')

	if not url:
		url = settings.get('integration_url')

	# check if only the integration key was given
	if len(url) == 32:
		url = 'https://events.pagerduty.com/integration/' + url + "/enqueue"

	body = json.dumps(payload)
	

	logger.info('Calling url="%s" with body=%s' % (url, body))

	req = urllib2.Request(url, body, {"Content-Type": "application/json"})
	try:
		res = urllib2.urlopen(req)
		body = res.read()
		pd_response = json.loads(body)
		logger.info("PagerDuty server responded with HTTP status=%d" % res.code)
		logger.info(body)
		if res.code < 200 or res.code > 299:
			return False
	except urllib2.HTTPError, e:
		logger.error("Error sending message: %s (%s)" % (e, str(dir(e))))
		return False

	event_id = payload['result']['event_id']
	session_key = payload['session_key']

	time.sleep(5) # wait 5 seconds for an incident to be created
	
	try:
		tries = 0
		while True:  # sometimes it takes a little while to get an incident, so retry for a bit if we don't get it the first time
			req = urllib2.Request("https://api.pagerduty.com/incidents?incident_key=%s" % event_id)
			req.add_header("Authorization", "Token token=%s" % token)
			req.add_header("Accept", "application/vnd.pagerduty+json;version=2")
			res = urllib2.urlopen(req)
			body = res.read()
			pd_response = json.loads(body)
			logger.info(body)
			if len(pd_response['incidents']) > 0:
				event = Event(session_key, logger)
				event.update_ticket_info(event_id, "PagerDuty", str(pd_response['incidents'][0]['incident_number']), pd_response['incidents'][0]['html_url'])
				event.create_comment(event_id, "Linked to PD incident at %s" % pd_response['incidents'][0]['html_url'])
				return True
			else:
				tries += 1
				if tries > 5:
					logger.error("Unable to create PD incident for event ID %s: timed out")
					event.create_comment(event_id, "Unable to create PD incident for event ID %s: timed out")
					return False
				logger.info("No incident yet, will check again in %d seconds" % (tries * 10))
				time.sleep(tries * 10)
	except urllib2.HTTPError, e:
		logger.error("Error sending message: %s (%s)" % (e, str(dir(e))))
		event.create_comment(event_id, "Unable to create PD incident for event ID %s: HTTPError: %s" % (event_id, e))
	except Exception as e:
		logger.error("Unknown error of type %s: %s" % (type(e).__name__, e))
		event.create_comment(event_id, "Unable to create PD incident for event ID %s: Unknown error: %s" % (event_id, e))

	return True



if __name__ == "__main__":
	logger = setup_logging("itsi_event_management.log", "itsi.event_action.pagerduty_itsi")
	if len(sys.argv) > 1 and sys.argv[1] == "--execute":
		payloadStr = sys.stdin.read()
		payload = json.loads(payloadStr)
		success = send_notification(payload, logger)
		if not success:
			logger.error("Failed trying to send incident alert")
			sys.exit(2)
		else:
			logger.info("Incident alert notification successfully sent")
	else:
		logger.error("FATAL Unsupported execution mode (expected --execute flag)")
		sys.exit(1)
