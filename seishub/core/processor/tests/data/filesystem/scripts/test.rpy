from seishub.core.processor.resources import resource

class MyGreatResource(resource.Resource):
    def render(self, request):
        return "<html>%s</html>" % request.method

resource = MyGreatResource()

