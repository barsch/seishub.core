from seishub.env import Environment
from twisted.internet import reactor 

RAW_XML1="""<station rel_uri="bern">
    <station_code>BERN</station_code>
    <chan_code>1</chan_code>
    <stat_type>0</stat_type>
    <lon>12.51200</lon>
    <lat>50.23200</lat>
    <stat_elav>0.63500</stat_elav>
    <XY>
        <paramXY color="green">20.5</paramXY>
        <paramXY>11.5</paramXY>
        <paramXY>blah</paramXY>
    </XY>
</station>"""

URI="/blah/blah"

env=Environment()
res=env.catalog.newXmlResource(URI,RAW_XML1)
idx=env.catalog.newXmlIndex("/station[./XY/paramXY]")
print idx.eval(res)
d=env.catalog.addResource(res)
d.addCallback(lambda foo: reactor.stop())
reactor.run()

