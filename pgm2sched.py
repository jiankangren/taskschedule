import json

class Task:
    def __init__(self,name,role,message):
        self.name = name
        self.role = role # aggregate messages, message, belief, observation
        self.factor = None
        self.message = message
        self.parents = []
        self.children = []
    def addchild(self,t):
        self.children.append(t)
        t.parents.append(self)
    def addparent(self,t):
        t.addchild(self)
    def __repr__(self):
        return "Task(%s,%s,#p%d,#c%d)" % (self.name,self.action,len(self.parents),len(self.children))

class Domain:
    def __init__(self,name,values):
        self.name = name
        self.values = values

class Node:
    def __init__(self,name,id):
        self.name = name
        self.id = id
        #for scheduling
        self.seenout = False
        self.seenouttask = None
        self.received = []

class VariableNode(Node):
    def __init__(self,name,id,role,xtype):
        Node.__init__(self,name,id)
        self.role = role
        self.xtype = xtype
        self.domain = None
        self.ddim = 0
        self.gdim = 0
    def inmessagetype(other):
        return (self.ddim,self.gdim)
        # always same as node
    def __repr__(self):
        return "VariableNode(%s,%s,dim=G%d/D%d)" % (self.name,self.xtype,self.gdim,self.ddim)

class FactorNode(Node):
    def __init__(self,name,id,xtype):
        Node.__init__(self,name,id)
        self.xtype = xtype
        self.vars = []
        self.dvars = []
        self.gvars = []
        self.ddim = 0
        self.gdim = 0
    def inmessagetype(other):
        # always as the variable connected 
        return other.inmessagetype()
    def __repr__(self):
        return "FactorNode(%s,%s,dim=G%d/D%d)" % (self.name,self.xtype,self.gdim,self.ddim)

class Pgm:
    def __init__(self,f):
        j = json.load(type(f) and open(f,"rb") or f)
        self.vars = {}
        self.domains = {}
        self.nodeid = {}
        self.facs = {}
        self.sched = []
        self.loaddomains(j["domains"])
        self.loadvars(j["variables"])
        self.loadfactors(j["factors"])
        self.loadsched(j["schedule"])
    def loaddomains(self,d):
        for v in d:
            name = v["name"]
            values = v["values"]
            self.domains[name] = Domain(name,values)
    def loadvars(self,d):
        for v in d:
            id = int(v["id"])
            name = v["name"]
            role = v["role"]
            xtype = v["type"]
            x = VariableNode(name,id,role,xtype)
            self.vars[name] = x
            self.nodeid[id] = x
            if xtype == "discrete":
                domain = v["domain"]
                x.domain = self.domains[domain]
                x.ddim = len(x.domain.values)
            else:
                dim = int(v["dim"])
                x.gdim = dim
    def loadfactors(self,d):
        for v in d:
            id = int(v["id"])
            name = v["name"]
            xtype = v["type"]
            g = FactorNode(name,id,xtype)           
            if xtype == "gmm":
                g.dvars = [self.vars[x] for x in v["discreteVars"]]
                g.gvars = [self.vars[x] for x in v["gaussianVars"]]
                g.vars = g.dvars + g.gvars
                g.gdim = sum([x.gdim for x in g.gvars])
                g.ddim = reduce(lambda x,y:x*y,[x.ddim for x in g.dvars],1)
                pass
            elif xtype == "discrete":
                g.vars = [self.vars[x] for x in v["variables"]]
                g.dvars = g.vars[:]
                g.ddim = reduce(lambda x,y:x*y,[x.ddim for x in g.vars],1)
                g.gdim = 0
                pass
            elif xtype == "gaussian":
                g.vars = [self.vars[x] for x in v["variables"]]
                g.gvars = g.vars[:]
                g.ddim = 0
                g.gdim = sum([x.gdim for x in g.vars])
                pass
            self.facs[name] = g
            self.nodeid[id] = g
    def loadsched(self,s):
        self.sched = [(self.nodeid[int(a["src"])],self.nodeid[int(a["dst"])]) for a in s["list"]]

def emitgraph(q,o):
    import pydot
    g = pydot.Dot(graph_type="graph")
    for v in q.nodeid.values():
        # make pydot objects with minimal writings of attributes for readability
        n = pydot.Node(v.name,label="%s\n%s G%d/D%d" % (v.name,v.xtype,v.gdim,v.ddim),shape=isinstance(v,VariableNode) and "ellipse" or "box")
        # TODO cost
        g.add_node(n)
    for f in q.facs.values():
        # make pydot objects with minimal writings of attributes for readability
        for v in f.vars:
            e = pydot.Edge(f.name,v.name)
            g.add_edge(e)
    if o.endswith(".png"):
        g.write_png(o)
    else:
        fp = open(o,"wb")
        fp.write(g.to_string())
        fp.close()

def emitdotsched(tasks,o):
    # EMIT sched.py compatible graph
    pass
def emitdot(tasks,o):
    import pydot
    g = pydot.Dot(graph_type="digraph")
    for t in tasks:
        # make pydot objects with minimal writings of attributes for readability
        n = pydot.Node(t.name)
        # TODO cost
        g.add_node(n)
    for t in tasks:
        # make pydot objects with minimal writings of attributes for readability
        for p in t.parents:
            e = pydot.Edge(p.name,t.name)
            g.add_edge(e)
    if o.endswith(".png"):
        g.write_png(o)
    else:
        fp = open(o,"wb")
        fp.write(g.to_string())
        fp.close()

if __name__ == "__main__":
    import sys
    q = Pgm(sys.argv[1])
    for a,b in q.sched:
        print a,"->",b
    print q.vars
    print q.facs
    emitgraph(q,"graph.png")

    print "TODO: cleanup some messages"

    tasks = []
    for src,dst in q.sched:
        t = Task("%s->%s" % (src.name,dst.name),"message",(src,dst))
        if src == dst:
            print "UNSUPPORTED NL SELF MESSAGE"
            break
        if not src.seenout:
            # this is the first output of the factor, if it has received message we need to create the seenout task
            # that collects 
            if len(src.received) == 0:
                # no need to create seenout
                print src.name,dst.name,"sends without having received"
                pass
            elif len(src.received) == 1:
                src.seenouttask = src.received[0]
                print src.name,dst.name,"sends having received 1"
                src.seenout = True
            else:
                print src.name,dst.name,"sends needs collecting",len(src.received)
                tt = Task("%s" % src.name,"collect",None)
                tt.factor = src
                tasks.append(tt)
                for q in src.received:
                    tt.addparent(q)
                src.seenouttask = tt
                src.seenout = True
        dst.received.append(t)
        if src.seenouttask is not None:
            t.addparent(src.seenouttask)
        tasks.append(t)

    emitdot(tasks,"out.png")
    emitdotsched(tasks,"out.dot")

    #sort topologically
    for q in tasks:
        print q.name,q.role,
        if len(q.parents) != 0:
            print "parents:",[x.name for x in q.parents]
        else:
            print


