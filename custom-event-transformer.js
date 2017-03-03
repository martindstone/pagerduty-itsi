var json = PD.inputRequest.body;
var result = json.result;

var search_name = json.search_name;
var component = result.component || "unknown component";
var host = result.host || "unknown host";
var time = parseFloat(json.result._time);
var creation_time = (isNaN(time) ? new Date() : new Date(time * 1000)).toISOString();
var log_level = json.result.log_level;
var status = json.result.status;
var source_type = json.result.sourcetype;
var splunk_server = json.result.splunk_server;
var index = json.result.index;
var results_link = json.results_link;

var severity = PD.Unknown;

switch (log_level) {
	case "5":
		severity = PD.Info;
		break;
	case "4":
		severity = PD.Info;
		break;
	case "3":
		severity = PD.Warning;
		break;
	case "2":
		severity = PD.Error;
		break;
	case "1":
		severity = PD.Critical;
		break;
	case "0":
		severity = PD.Critical;
}

var cef_event = {
	dedup_key: json.result.event_id,
	event_action: PD.Trigger,
	client: "Splunk",
	client_url: results_link,
	details: result,
	local_instance_id: `${splunk_server}-${host}-${component}`,
	creation_time: creation_time,
	severity: severity,
	message: result.title,
	description: result.description,
	event_class: status,
	source_origin: host,
	source_component: source_type,
	reporter_location: splunk_server,
	service_group: index
};

PD.emitCEFEvents([cef_event]);