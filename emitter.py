# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
from hashlib import md5
import logging
import re
import string
import zlib
import unicodedata

# 3p
import requests
import simplejson as json

# project
from config import get_version

from utils.proxy import set_no_proxy_settings
set_no_proxy_settings()

# urllib3 logs a bunch of stuff at the info level
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.WARN)
requests_log.propagate = True

# From http://stackoverflow.com/questions/92438/stripping-non-printable-characters-from-a-string-in-python
control_chars = ''.join(map(unichr, range(0, 32) + range(127, 160)))
control_char_re = re.compile('[%s]' % re.escape(control_chars))


# Only enforced for the metrics API on our end, for now
MAX_COMPRESSED_SIZE = 2 << 20  # 2MB, the backend should accept up to 3MB but let's be conservative here
# maximum depth of recursive calls to payload splitting function, a bit arbitrary (we don't want too much
# depth in the recursive calls, but we want to give up only when some metrics are clearly too large)
MAX_SPLIT_DEPTH = 2


def remove_control_chars(s, log):
    if isinstance(s, str):
        sanitized = control_char_re.sub('', s)
    elif isinstance(s, unicode):
        sanitized = ''.join(['' if unicodedata.category(c) in ['Cc','Cf'] else c
                            for c in u'{}'.format(s)])
    if sanitized != s:
        log.warning('Removed control chars from string: ' + s)
    return sanitized

def remove_undecodable_chars(s, log):
    sanitized = s
    if isinstance(s, str):
        try:
            s.decode('utf8')
        except UnicodeDecodeError:
            sanitized = s.decode('utf8', errors='ignore')
            log.warning(u'Removed undecodable chars from string: ' + s.decode('utf8', errors='replace'))
    return sanitized

def sanitize_payload(item, log, sanitize_func):
    if isinstance(item, dict):
        newdict = {}
        for k, v in item.iteritems():
            newval = sanitize_payload(v, log, sanitize_func)
            newkey = sanitize_func(k, log)
            newdict[newkey] = newval
        return newdict
    if isinstance(item, list):
        newlist = []
        for listitem in item:
            newlist.append(sanitize_payload(listitem, log, sanitize_func))
        return newlist
    if isinstance(item, tuple):
        newlist = []
        for listitem in item:
            newlist.append(sanitize_payload(listitem, log, sanitize_func))
        return tuple(newlist)
    if isinstance(item, basestring):
        return sanitize_func(item, log)

    return item


def post_payload(url, message, serialize_func, agentConfig, log):
    agentKey = message.get('agentKey', None)
    if not agentKey:
        raise Exception("The http emitter requires an agent key")
    url = "{0}/intake/{1}?agent_key={2}".format(url, "", agentKey)
    log.debug('http_emitter: attempting postback to ' + string.split(url, "agent_key=")[0])
    try:
        payloads = serialize_func(message, MAX_COMPRESSED_SIZE, 0, log)
    except UnicodeDecodeError:
        log.exception('http_emitter: Unable to convert message to json')
        # early return as we can't actually process the message
        return
    except RuntimeError:
        log.exception('http_emitter: runtime error dumping message to json')
        # early return as we can't actually process the message
        return
    except Exception:
        log.exception('http_emitter: unknown exception processing message')
        return

    for payload in payloads:
        try:
            headers = get_post_headers(agentConfig, payload)
            r = requests.post(url, data=payload, timeout=5, headers=headers)

            r.raise_for_status()

            if r.status_code >= 200 and r.status_code < 205:
                log.debug("Payload accepted")
        except Exception as e:
            log.error("Unable to post payload: %s" % e.message)


def serialize_payload(message, log):
    payload = ""
    try:
        payload = json.dumps(message)
    except UnicodeDecodeError:
        newmessage = sanitize_payload(message, log, remove_control_chars)
        try:
            payload = json.dumps(newmessage)
        except UnicodeDecodeError:
            log.info('Removing undecodable characters from payload')
            newmessage = sanitize_payload(newmessage, log, remove_undecodable_chars)
            payload = json.dumps(newmessage)

    return payload


def serialize_and_compress_legacy_payload(legacy_payload, max_compressed_size, depth, log):
    """
    Serialize and compress the legacy payload
    """
    serialized_payload = serialize_payload(legacy_payload, log)
    zipped = zlib.compress(serialized_payload)
    log.debug("payload_size=%d, compressed_size=%d, compression_ratio=%.3f"
              % (len(serialized_payload), len(zipped), float(len(serialized_payload))/float(len(zipped))))


    compressed_payloads = [zipped]

    if len(zipped) > max_compressed_size:
        # let's just log a warning for now, splitting the legacy payload is tricky
        log.warning("collector payload is above the limit of %dKB compressed", max_compressed_size/(1 << 10))

    return compressed_payloads


def serialize_and_compress_metrics_payload(metrics_payload, max_compressed_size, depth, log):
    """
    Serialize and compress the metrics payload
    If the compressed payload is too big, we attempt to split it into smaller payloads and call this
    function recursively on each smaller payload
    """
    compressed_payloads = []

    serialized_payload = serialize_payload(metrics_payload, log)
    zipped = zlib.compress(serialized_payload)
    compression_ratio = float(len(serialized_payload))/float(len(zipped))
    log.debug("payload_size=%d, compressed_size=%d, compression_ratio=%.3f"
              % (len(serialized_payload), len(zipped), compression_ratio))

    if len(zipped) < max_compressed_size:
        compressed_payloads.append(zipped)
    else:
        series = metrics_payload["series"]

        if depth > MAX_SPLIT_DEPTH:
            log.error("Maximum depth of payload splitting reached, dropping the %d metrics in this chunk", len(series))
            return compressed_payloads

        # Try to account for the compression when estimating the number of chunks needed to get small-enough chunks
        n_chunks = len(zipped)/max_compressed_size + 1 + int(compression_ratio/2)
        log.debug("payload is too big (%d bytes), splitting it in %d chunks", len(zipped), n_chunks)

        series_per_chunk = len(series)/n_chunks + 1

        for i in range(n_chunks):
            # Create each chunk and make them go through this function recursively ; increment the `depth` of the recursive call
            compressed_payloads.extend(
                serialize_and_compress_metrics_payload(
                    {
                        "series": series[i*series_per_chunk:(i+1)*series_per_chunk]
                    },
                    max_compressed_size,
                    depth+1,
                    log
                )
            )

    return compressed_payloads


def serialize_and_compress_checkruns_payload(checkruns_payload, max_compressed_size, depth, log):
    """
    Serialize and compress the checkruns payload
    """
    serialized_payload = serialize_payload(checkruns_payload, log)
    zipped = zlib.compress(serialized_payload)
    log.debug("payload_size=%d, compressed_size=%d, compression_ratio=%.3f"
              % (len(serialized_payload), len(zipped), float(len(serialized_payload))/float(len(zipped))))

    compressed_payloads = [zipped]

    if len(zipped) > max_compressed_size:
        # let's just log a warning for now, splitting the legacy payload is tricky
        log.warning("checkruns payload is above the limit of %dKB compressed", max_compressed_size/(1 << 10))

    return compressed_payloads


def split_payload(legacy_payload):
    metrics_payload = {"series": []}

    for ts in legacy_payload['metrics']:
        sample = {
            "metric": ts[0],
            "points": [(ts[1], ts[2])],
            "source_type_name": "System",
        }

        if len(ts) >= 4:
            # Default to the metric hostname if present
            if ts[3].get('hostname'):
                sample['host'] = ts[3]['hostname']
            else:
                # If not use the general payload one
                sample['host'] = legacy_payload['internalHostname']

            if ts[3].get('type'):
                sample['type'] = ts[3]['type']
            if ts[3].get('tags'):
                sample['tags'] = ts[3]['tags']
            if ts[3].get('device_name'):
                sample['device'] = ts[3]['device_name']

        metrics_payload["series"].append(sample)

    del legacy_payload['metrics']

    checkruns_payload = legacy_payload["service_checks"]

    del legacy_payload["service_checks"]

    return legacy_payload, metrics_payload, checkruns_payload


def http_emitter(message, log, agentConfig, endpoint):
    agent_key = message.get('agentKey')

    if not agent_key:
        raise Exception("The http emitter requires an agentkey")
    url = agentConfig['sd_url']

    # Post metrics payload
    post_payload(url, message, serialize_and_compress_metrics_payload, agentConfig, log)


def get_post_headers(agentConfig, payload):
    return {
        'User-Agent': 'Server Density Agent/%s' % agentConfig['version'],
        'Content-Type': 'application/json',
        'Content-Encoding': 'deflate',
        'Accept': 'text/html, */*',
        'Content-MD5': md5(payload).hexdigest(),
        'SD-Collector-Version': get_version()
    }
