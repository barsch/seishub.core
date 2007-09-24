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
        report = """\
<UL>
    <LI>The path to me is %(path)s
    <LI>The host I'm on is %(host)s
    <LI>The port I'm on is %(port)s
    <LI>I was accessed %(secure)s
    <LI>A URL to me is %(url)s
    <LI>My URI to me is %(uri)s
    </UL>
""" % vars()
        output = Template(file="seishub/services/rest/tmpl/index.tmpl")
        output.title = "Web/REST"
        request.write(str(output) + report)
        return ""
        
