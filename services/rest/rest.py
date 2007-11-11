# -*- coding: utf-8 -*-

from twisted.web import resource
from Cheetah.Template import Template


class RESTService(resource.Resource):
    def __init__(self):
        resource.Resource.__init__(self)
        
    def render_GET(self, request):
        path = request.path
        _, host, port = request.getHost()
        url = request.prePathURL()
        uri = request.uri
        secure = (request.isSecure() and "securely") or "insecurely"
        report = \
"""<ul>
    <li>The path to me is %(path)s</li>
    <li>The host I'm on is %(host)s</li>
    <li>The port I'm on is %(port)s</li>
    <li>I was accessed %(secure)s</li>
    <li>A URL to me is %(url)s</li>
    <li>My URI to me is %(uri)s</li>
</ul>""" % (path,host,port,secure,url,uri)
        output = Template(file="seishub/services/rest/tmpl/index.tmpl")
        output.title = "Web/REST"
        request.write(str(output) + report)
        return ""
        
