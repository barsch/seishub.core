from twisted.internet import reactor
import sqlalchemy as sa
from sasync.database import AccessBroker, transact

class TestAB(AccessBroker):
    def startup(self):
        # This method can also be 'userStartup' instead of 'startup', due to
        # backwards compatibility.
        return self.table('accounts',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('name', sa.String(255)),
            sa.Column('password', sa.String(255))
        )

    @transact
    def insertUser(self, name, password):
        return self.accounts.insert().execute(name=name, password=password)

    @transact
    def getUsers(self):
        return self.accounts.select().execute().fetchall()

def insert(ab):    
    return ab.insertUser('Joe Schmortz', 'secret!')
       
def select(ab):
    def stopAndDisplay(queryResult):        
        print repr(queryResult)
        reactor.stop()
        
    return ab.getUsers().addCallback(stopAndDisplay)
    
def start():
    broker = TestAB("sqlite://./test.db")
    d = broker.startup()
    # Only Once the AccessBroker starts up can we use it
    d = d.addCallback(lambda _: insert(broker))    
    d.addCallback(lambda _: select(broker))            
    # Start up the reactor
    reactor.run()
    
if __name__ == "__main__":
    start()
