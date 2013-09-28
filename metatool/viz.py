import plugin as plugin

nodemakers = plugin.load_nodemakers()

def get_nodes(modeltype, model_stream, **nodemaker_options):
    for name, nodemaker in nodemakers.iteritems():
        if nodemaker.supports(modeltype, **nodemaker_options):
            nodes = nodemaker.get_nodes(modeltype, model_stream, **nodemaker_options)
            return nodes
    return {}
