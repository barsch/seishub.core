

class Tree:
    """A simple tree object.
    
    Nodes are added by providing an absolute paths and a mapped object.
    """
    def __init__(self):
        self.children = {}
    
    def add(self, path, obj):
        """Add a node to the tree by given path and mapped object."""
        parts = self._postProcessPath(path)
        temp = self.children
        for part in parts[:-1]:
            if part not in temp:
                temp[part] = {}
            temp=temp[part]
        temp[parts[-1]] = obj
    
    def __str__(self):
        return str(self.children)
    
    def get(self, path=''):
        """Try to get objects or sub nodes of a path."""
        parts = self._postProcessPath(path)
        temp = self.children
        try:
            for part in parts:
                temp=temp.get(part)
            return temp
        except AttributeError:
            return temp
    
    def isLeaf(self, path=''):
        """Check if the current path is a object or sub node."""
        temp = self.get(path)
        if isinstance(temp, dict):
            return False
        if not temp:
            return False
        return True
    
    def _postProcessPath(self, path=''):
        """Post process the given path."""
        if isinstance(path, list):
            return path
        # remove starting slash
        if path.startswith('/'):
            path = path[1:]
        # remove trailing slash
        if path.endswith('/'):
            path = path[:-1]
        # split for path sub elements
        parts=path.split('/')
        if parts==['']:
            return []
        return parts
