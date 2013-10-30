
/*
 * Render a pure graphviz definition to the svg specified by svg selector.
 */
function renderDotToD3(graphDef, svgSelector) {
  var result = dagre.dot.toObjects(graphDef);
  renderDagreObjsToD3({nodes: result.nodes, edges: result.edges}, svgSelector);
}

/*
 *  Render javascript edges and nodes to the svg.  This method should be more
 *  convenient when data was serialized as json and node definitions would be duplicated
 *  if edges had direct references to nodes.  See state-graph-js.html for example.
 */
function renderJSObjsToD3(nodeData, edgeData, svgSelector) {
  var nodeRefs = [];
  var edgeRefs = [];
  var idCounter = 0;

  edgeData.forEach(function(e){
    edgeRefs.push({
      source: nodeData[e.source],
      target: nodeData[e.target],
      label: e.label,
      id: e.id !== undefined ? e.id : (idCounter++ + "|" + e.source + "->" + e.target)
    });
  });

  for (var nodeKey in nodeData) {
    if (nodeData.hasOwnProperty(nodeKey)) {
      var u = nodeData[nodeKey];
      if (u.id === undefined) {
        u.id = nodeKey;
      }
      nodeRefs.push(u);
    }
  }

  renderDagreObjsToD3({nodes: nodeRefs, edges: edgeRefs}, svgSelector);
}

function initViz(svgSelector) {
    
    var svg = d3.select(svgSelector);

    // set up the arrowhead specification
    if (svg.select("#arrowhead").empty()) {
    svg.append('svg:defs').append('svg:marker')
      .attr('id', 'arrowhead')
      .attr('viewBox', '0 0 10 10')
      .attr('refX', 8)
      .attr('refY', 5)
      .attr('markerUnits', 'strokewidth')
      .attr('markerWidth', 8)
      .attr('markerHeight', 5)
      .attr('orient', 'auto')
      .attr('style', 'fill: #333')
      .append('svg:path')
      .attr('d', 'M 0 0 L 10 5 L 0 10 z');
    }

    // re-init the vis - remove any old groups and start again from scratch
    svg.selectAll("g").remove();
    svg.append("g");
    var svgGroup = svg.select("g")
    
    // Add zoom behavior to the SVG canvas
    svgGroup.attr("transform", "translate(5, 5)");
    svg.call(d3.behavior.zoom().on("zoom", function redraw() {
    svgGroup.attr("transform",
      "translate(" + d3.event.translate + ")" + " scale(" + d3.event.scale + ")");
    }));
}

function updateViz(graphData, svgSelector) {
    var nodeData = graphData.nodes;
    var edgeData = graphData.edges;

    var uptodateNodes = []
    var uptodateEdges = []

    var svg = d3.select(svgSelector);
    var svgGroup = svg.select("g")
    
    // create all the new nodes from the data, keyed by their id
    // for all nodes, set their nodePadding property
    var nodes = svgGroup
    .selectAll("g .node")
    .data(nodeData, function(d) { return d.id })
    
    // remove the exit nodes altogether
    nodes.exit().remove()
    
    // add all the new nodes
    nodes.enter()
        .append("g")
        .attr("class", function (d) {
          if (d.nodeclass) {
            return "node " + d.nodeclass;
          } else {
            return "node";
          }
        })
        .attr("id", function (d) {
          return "node-" + d.id;
        })
    
    // remove all the children of the all node groups - we need to start again from scratch
    nodes.selectAll("*").remove()
    
    // now set the core node properties
    nodes
        .each(function (d) {
          d.nodePadding = 10;
        });

    // append a "rect" element to each new node
    nodes.append("rect");

    // add the label placeholders to each node
    addLabels(nodes);

    // create all of the new edges from the data, keyed by their id
    var edges = svgGroup
        .selectAll("g .edge")
        .data(edgeData, function(d) { return d.id })
    
    // remove the exit edges altogether
    edges.exit().remove()
    
    // add all the new edges
    edges.enter()
        .append("g")
        .attr("class", function (d) {
          if (d.edgeclass) {
            return "edge " + d.edgeclass;
          } else {
            return "edge";
          }
        })
        .attr("id", function (d) {
          return "edge-" + d.id;
        })

    // remove all the children of the all edge groups - we need to start again from scratch
    edges.selectAll("*").remove()

    // for each edge, add a path with an arrow head
    edges
        .each(function (d) {
          d.nodePadding = 0;
        })
        .append("path")
        .attr("marker-end", "url(#arrowhead)");
    
    // add the label placeholders
    addLabels(edges);
    
    // select all of the labels we created with placeholders above
    var labelGroup = svgGroup.selectAll("g.label");

    // from the label group get all the foreign object labels
    var foLabel = labelGroup
    .selectAll(".htmllabel")
    // TODO find a better way to get the dimensions for foriegnObjects
    .attr("width", "100000");

    // set the attributes of all the foreign object labels
    foLabel
    .select("div")
    .html(function (d) {
      return d.label;
    })
    .each(function (d) {
      d.width = this.clientWidth;
      d.height = this.clientHeight;
      d.nodePadding = 0;
    });

    foLabel
    .attr("width", function (d) {
      return d.width;
    })
    .attr("height", function (d) {
      return d.height;
    });

    // from the label group, get all of the text labels
    var textLabel = labelGroup
    .filter(function (d) {
      return d.label && d.label[0] !== "<";
    });

    // add all the label text to the text labels!
    //textLabel
    //.select("text")
    //.attr("text-anchor", "left")
    //.append("tspan")
    //.attr("dy", "1em")
    //.text(function (d) {
    //  return d.label;
    //});
    
    // remove the existing labels from everything
    textLabel
    .select("text")
    .attr("text-anchor", "left")
    .selectAll("tspan").remove()
    
    // re-add the existing labels and add for the first time all the new ones
    textLabel
    .select("text")
    .append("tspan")
    .attr("dy", "1em")
    .text(function (d) {
      return d.label;
    });

    // for each label, get its bounding box, and set the width and height based on this info
    labelGroup
    .each(function (d) {
      var bbox = this.getBBox();
      d.bbox = bbox;

      d.width = bbox.width + 2 * d.nodePadding;
      d.height = bbox.height + 2 * d.nodePadding;

    });

    // get the up-to-date node and edge data out of the nodes
    nodes.each(function(d) { uptodateNodes.push(d) })
    edges.each(function(d) { uptodateEdges.push(d) })

    // Run the actual layout through the dagre library - it requires all of the above
    // to be in-place on the svg canvas before it will work (or does it - maybe it's just
    // the label bounding boxes that need to have been calculated?)
    dagre.layout()
    .nodes(uptodateNodes)
    .edges(uptodateEdges)
    .rankSep(100)
    .rankDir("LR")
    .run();

    // for each existing node (created from the data points), set its
    // - position (via translate)
    // then create a rectangle with the following properties:
    // - rounding of the box corners (by rx and ry)
    // - x and y coordinates (relative to the translate point) based on the bounding box and padding
    // - width and height
    nodes
    .attr("transform", function (d) {
      return "translate(" + d.dagre.x + "," + d.dagre.y + ")";
    })
    .selectAll("g.node rect")
    .attr("rx", 5)
    .attr("ry", 5)
    .attr("x", function (d) {
      return -(d.bbox.width / 2 + d.nodePadding);
    })
    .attr("y", function (d) {
      return -(d.bbox.height / 2 + d.nodePadding);
    })
    .attr("width", function (d) {
      return d.width;
    })
    .attr("height", function (d) {
      return d.height;
    });

    // for each existing edge (created from its data points), create a path
    // the path's data points are created from a function which uses the
    // dagre library to work out.  It's too clever for me to retrospectively document :)
    edges
    .selectAll("path")
    .attr("d", function (d) {
      var points = d.dagre.points.slice(0);
      points.unshift(dagre.util.intersectRect(d.source.dagre, points[0]));

      var preTarget = points[points.length - 2];
      var target = dagre.util.intersectRect(d.target.dagre, points[points.length - 1]);

      //  This shortens the line by a couple pixels so the arrowhead won't overshoot the edge of the target
      var deltaX = preTarget.x - target.x;
      var deltaY = preTarget.y - target.y;
      var m = 2 / Math.sqrt(Math.pow(deltaX, 2) + Math.pow(deltaY, 2));
      points.push({
          x: target.x + m * deltaX,
          y: target.y + m * deltaY
        }
      );

      return d3.svg.line()
        .x(function (e) {
          return e.x;
        })
        .y(function (e) {
          return e.y;
        })
        .interpolate("bundle")
        .tension(.8)
        (points);
    });

    // for every rectangle in the diagram
    // - shift everything by the node padding up and left (why? dunno, but it is required to line everything up)
    // - set the width and the height (again?)
    svgGroup
    .selectAll("g.label rect")
    .attr("x", function (d) {
      return -d.nodePadding;
    })
    .attr("y", function (d) {
      return -d.nodePadding;
    })
    .attr("width", function (d) {
      return d.width;
    })
    .attr("height", function (d) {
      return d.height;
    });

    // for each node get their labels, and transform their position in a way
    // I don't totally get
    nodes
    .selectAll("g.label")
    .attr("transform", function (d) {
      return "translate(" + (-d.bbox.width / 2) + "," + (-d.bbox.height / 2) + ")";
    });

    // for each edge, get their labels, and transform their position in another
    // way that I don't totally get
    edges
    .selectAll("g.label")
    .attr("transform", function (d) {
      var points = d.dagre.points;

      if (points.length > 1) {
        var x = (points[0].x + points[1].x) / 2;
        var y = (points[0].y + points[1].y) / 2;
        return "translate(" + (-d.bbox.width / 2 + x) + "," + (-d.bbox.height / 2 + y) + ")";
      } else {
        return "translate(" + (-d.bbox.width / 2 + points[0].x) + "," + (-d.bbox.height / 2 + points[0].y) + ")";
      }
    });
}

/*
 *  Render javscript objects to svg, as produced by  dagre.dot.
 */
function renderDagreObjsToD3(graphData, svgSelector) {
  var nodeData = graphData.nodes;
  var edgeData = graphData.edges;

  var svg = d3.select(svgSelector);

  // set up the arrowhead specification
  if (svg.select("#arrowhead").empty()) {
    svg.append('svg:defs').append('svg:marker')
      .attr('id', 'arrowhead')
      .attr('viewBox', '0 0 10 10')
      .attr('refX', 8)
      .attr('refY', 5)
      .attr('markerUnits', 'strokewidth')
      .attr('markerWidth', 8)
      .attr('markerHeight', 5)
      .attr('orient', 'auto')
      .attr('style', 'fill: #333')
      .append('svg:path')
      .attr('d', 'M 0 0 L 10 5 L 0 10 z');
  }

  // re-init the vis - remove any old groups and start again from scratch
  svg.selectAll("g").remove();
  var svgGroup = svg.append("g");
  
  // create all the new nodes from the data, keyed by their id
  var nodes = svgGroup
    .selectAll("g .node")
    .data(nodeData, function(d) { return d.id });

  // add all the new nodes
  var nodeEnter = nodes
    .enter()
    .append("g")
    .attr("class", function (d) {
      if (d.nodeclass) {
        return "node " + d.nodeclass;
      } else {
        return "node";
      }
    })
    .attr("id", function (d) {
      return "node-" + d.id;
    })
    .each(function (d) {
      d.nodePadding = 10;
    });
    
  // append a "rect" element to each new node
  nodeEnter.append("rect");
  
  // add the label placeholders to each node
  addLabels(nodeEnter);
  
  // remove any unwanted nodes
  nodes.exit().remove();

  // create all of the new edges from the data, keyed by their id
  var edges = svgGroup
    .selectAll("g .edge")
    .data(edgeData, function(d) { return d.id })
    .each(function (d) {
      d.nodePadding = 0;
    });

  // add all the new edges
  var edgeEnter = edges
    .enter()
    .append("g")
    .attr("class", "edge")
    .attr("id", function (d) {
      return "edge-" + d.id;
    })
    .each(function (d) {
      d.nodePadding = 0;
    });

  // for each edge, add a path with an arrow head
  edgeEnter
    .append("path")
    .attr("marker-end", "url(#arrowhead)");
    
  // add the label placeholders
  addLabels(edgeEnter);
  
  // remove any unwanted edges
  edges.exit().remove();

  // select all of the labels we created with placeholders above
  var labelGroup = svgGroup.selectAll("g.label");

  // from the label group get all the foreign object labels
  var foLabel = labelGroup
    .selectAll(".htmllabel")
    // TODO find a better way to get the dimensions for foriegnObjects
    .attr("width", "100000");

  // set the attributes of all the foreign object labels
  foLabel
    .select("div")
    .html(function (d) {
      return d.label;
    })
    .each(function (d) {
      d.width = this.clientWidth;
      d.height = this.clientHeight;
      d.nodePadding = 0;
    });

  foLabel
    .attr("width", function (d) {
      return d.width;
    })
    .attr("height", function (d) {
      return d.height;
    });

  // from the label group, get all of the text labels
  var textLabel = labelGroup
    .filter(function (d) {
      return d.label && d.label[0] !== "<";
    });

  // add all the label text to the text labels!
  textLabel
    .select("text")
    .attr("text-anchor", "left")
    .append("tspan")
    .attr("dy", "1em")
    .text(function (d) {
      return d.label;
    });

  // for each label, get its bounding box, and set the width and height based on this info
  labelGroup
    .each(function (d) {
      var bbox = this.getBBox();
      d.bbox = bbox;

      d.width = bbox.width + 2 * d.nodePadding;
      d.height = bbox.height + 2 * d.nodePadding;

    });

  // Add zoom behavior to the SVG canvas
  svgGroup.attr("transform", "translate(5, 5)");
  svg.call(d3.behavior.zoom().on("zoom", function redraw() {
    svgGroup.attr("transform",
      "translate(" + d3.event.translate + ")" + " scale(" + d3.event.scale + ")");
  }));

  // Run the actual layout through the dagre library - it requires all of the above
  // to be in-place on the svg canvas before it will work (or does it - maybe it's just
  // the label bounding boxes that need to have been calculated?)
  dagre.layout()
    .nodes(nodeData)
    .edges(edgeData)
    .rankSep(100)
    .rankDir("LR")
    .run();

  // for each existing node (created from the data points), set its
  // - position (via translate)
  // then create a rectangle with the following properties:
  // - rounding of the box corners (by rx and ry)
  // - x and y coordinates (relative to the translate point) based on the bounding box and padding
  // - width and height
  nodes
    .attr("transform", function (d) {
      return "translate(" + d.dagre.x + "," + d.dagre.y + ")";
    })
    .selectAll("g.node rect")
    .attr("rx", 5)
    .attr("ry", 5)
    .attr("x", function (d) {
      return -(d.bbox.width / 2 + d.nodePadding);
    })
    .attr("y", function (d) {
      return -(d.bbox.height / 2 + d.nodePadding);
    })
    .attr("width", function (d) {
      return d.width;
    })
    .attr("height", function (d) {
      return d.height;
    });

  // for each existing edge (created from its data points), create a path
  // the path's data points are created from a function which uses the
  // dagre library to work out.  It's too clever for me to retrospectively document :)
  edges
    .selectAll("path")
    .attr("d", function (d) {
      var points = d.dagre.points.slice(0);
      points.unshift(dagre.util.intersectRect(d.source.dagre, points[0]));

      var preTarget = points[points.length - 2];
      var target = dagre.util.intersectRect(d.target.dagre, points[points.length - 1]);

      //  This shortens the line by a couple pixels so the arrowhead won't overshoot the edge of the target
      var deltaX = preTarget.x - target.x;
      var deltaY = preTarget.y - target.y;
      var m = 2 / Math.sqrt(Math.pow(deltaX, 2) + Math.pow(deltaY, 2));
      points.push({
          x: target.x + m * deltaX,
          y: target.y + m * deltaY
        }
      );

      return d3.svg.line()
        .x(function (e) {
          return e.x;
        })
        .y(function (e) {
          return e.y;
        })
        .interpolate("bundle")
        .tension(.8)
        (points);
    });

  // for every rectangle in the diagram
  // - shift everything by the node padding up and left (why? dunno, but it is required to line everything up)
  // - set the width and the height (again?)
  svgGroup
    .selectAll("g.label rect")
    .attr("x", function (d) {
      return -d.nodePadding;
    })
    .attr("y", function (d) {
      return -d.nodePadding;
    })
    .attr("width", function (d) {
      return d.width;
    })
    .attr("height", function (d) {
      return d.height;
    });

  // for each node get their labels, and transform their position in a way
  // I don't totally get
  nodes
    .selectAll("g.label")
    .attr("transform", function (d) {
      return "translate(" + (-d.bbox.width / 2) + "," + (-d.bbox.height / 2) + ")";
    });

  // for each edge, get their labels, and transform their position in another
  // way that I don't totally get
  edges
    .selectAll("g.label")
    .attr("transform", function (d) {
      var points = d.dagre.points;

      if (points.length > 1) {
        var x = (points[0].x + points[1].x) / 2;
        var y = (points[0].y + points[1].y) / 2;
        return "translate(" + (-d.bbox.width / 2 + x) + "," + (-d.bbox.height / 2 + y) + ")";
      } else {
        return "translate(" + (-d.bbox.width / 2 + points[0].x) + "," + (-d.bbox.height / 2 + points[0].y) + ")";
      }
    });
}

// add all the placeholders for the labels
function addLabels(selection) {

  var labelGroup = selection
    .append("g")
    .attr("class", "label");
  labelGroup.append("rect");

  var foLabel = labelGroup
    .filter(function (d) {
      return d.label && d.label[0] === "<";
    })
    .append("foreignObject")
    .attr("class", "htmllabel");

  foLabel
    .append("xhtml:div")
    .style("float", "left");

  labelGroup
    .filter(function (d) {
      return d.label && d.label[0] !== "<";
    })
    .append("text")
}
