import networkx as nx
from services.sparql_service import get_entity_details
import plotly.graph_objects as go
import json
import numpy as np
import re



def generate_knowledge_graph(entity_id, depth=1, max_relations=15):
    """
    Generate a knowledge graph for visualization starting from the given entity
    Returns data structure suitable for visualization
    """
    # Create a directed graph
    G = nx.DiGraph()
    
    # Start with the main entity
    entity_data = get_entity_details(entity_id)
    if not entity_data:
        print(f"No entity data found for {entity_id}")
        # Create a minimal graph with just the entity
        G.add_node(entity_id, label=entity_id, type="main", image=None)
        nodes = [{"id": entity_id, "label": entity_id, "type": "main"}]
        return {"nodes": nodes, "links": []}
    
    # Add the main entity as a node
    G.add_node(entity_id, 
              label=entity_data["label"], 
              type="main",
              image=None)  # Main entity is centered
    
    # Add edges for each property (limited to max_relations)
    relations_added = 0
    
    # Process properties
    if not entity_data.get("properties"):
        print(f"No properties found for entity {entity_id}")
        nodes = [{"id": entity_id, "label": entity_data["label"], "type": "main"}]
        return {"nodes": nodes, "links": []}
    
    for prop in entity_data["properties"][:max_relations*2]:  # Look at more properties
        # Skip certain internal property IDs
        if prop["id"] in ["P31", "P21"]:
            continue
            
        # Determine if this property represents an entity or media
        is_wikidata = "wikidata.org/entity/" in prop["raw_value"]
        is_commons = "commons.wikimedia.org" in prop["raw_value"] or "wikimedia.org/wiki" in prop["raw_value"]
        is_url = prop["raw_value"].startswith("http") and not is_wikidata
        
        # Generate a property-specific ID, avoiding URL prefix display
        if "P" in prop["id"]:
            relation_label = f"Property:{prop['id']}"
        else:
            relation_label = prop["label"]
        
        # Handle entity references
        if is_wikidata:
            object_id = prop["raw_value"].split("/")[-1]
            
            # Determine node type
            node_type = "related"
            
            # Check property type
            if "location" in prop["label"].lower() or "place" in prop["label"].lower() or "country" in prop["label"].lower():
                node_type = "location"
            elif ("person" in prop["label"].lower() or "creator" in prop["label"].lower() or 
                  "author" in prop["label"].lower() or "director" in prop["label"].lower() or
                  "founder" in prop["label"].lower() or "head" in prop["label"].lower()):
                node_type = "person"
            
            # Add the object entity as a node
            G.add_node(object_id, 
                      label=prop["value"], 
                      type=node_type,
                      image=None)
            
            # Add an edge from the main entity to this object
            G.add_edge(entity_id, object_id, label=relation_label, relationship=relation_label)
            
            relations_added += 1
        
        # Handle Commons files and images
        elif is_commons or ("image" in prop["label"].lower() and is_url):
            # For Commons files, try to get a clean ID
            if is_commons:
                if "File:" in prop["raw_value"]:
                    parts = prop["raw_value"].split("File:")
                    file_name = parts[1].split("?")[0].replace("_", " ")
                    clean_id = f"File:{file_name}"
                else:
                    clean_id = f"media_{relations_added}"
            else:
                clean_id = f"media_{relations_added}"
            
            # Add as an image node
            G.add_node(clean_id, 
                      label=prop["value"] if len(prop["value"]) < 30 else prop["value"][:27] + "...", 
                      type="image",
                      image=prop["raw_value"])
            
            # Add an edge
            G.add_edge(entity_id, clean_id, label=relation_label, relationship=relation_label)
            
            relations_added += 1
            
        if relations_added >= max_relations:
            break
    
    # Convert NetworkX graph to a format suitable for visualization
    nodes = []
    for node_id, data in G.nodes(data=True):
        node_info = {
            "id": node_id,
            "label": data.get("label", node_id),
            "type": data.get("type", "default")
        }
        # Add image URL if available
        if data.get("image"):
            node_info["image"] = data["image"]
        nodes.append(node_info)
    
    links = []
    for source, target, data in G.edges(data=True):
        links.append({
            "source": source,
            "target": target,
            "label": data.get("label", "related to"),
            "relationship": data.get("relationship", "related to")
        })

    # Add a check to make sure we have nodes
    if not nodes:
        nodes = [{"id": entity_id, "label": entity_data["label"], "type": "main"}]
    
    return {
        "nodes": nodes,
        "links": links
    }

def generate_3d_graph_html(graph_data):
    """
    Generate an HTML string containing a 2D force-directed graph visualization
    Uses D3.js for visualization to display images directly in nodes
    """
    # Convert graph data to D3 format
    nodes = graph_data["nodes"]
    links = graph_data["links"]
    
    if not nodes:
        return "<div class='error'>No graph data available</div>"
    
    # Prepare data for D3.js
    d3_nodes = []
    for node in nodes:
        node_data = {
            "id": node["id"],
            "label": node["label"],
            "type": node["type"]
        }
        # Add image URL if available
        if "image" in node and node["image"]:
            node_data["image"] = node["image"]
        d3_nodes.append(node_data)
    
    d3_links = []
    for link in links:
        d3_links.append({
            "source": link["source"],
            "target": link["target"],
            "label": link["label"]
        })
    
    # Create a D3.js force-directed graph
    d3_data = {
        "nodes": d3_nodes,
        "links": d3_links
    }
    
    # Generate HTML with embedded D3.js visualization
    html_content = f"""
    <div id="knowledge-graph-container" style="width:100%; height:600px; border:1px solid #ddd; position:relative;">
        <div id="graph-legend" style="position:absolute; top:10px; right:10px; background:rgba(255,255,255,0.9); padding:10px; border-radius:5px; z-index:1000;">
            <div><span style="display:inline-block; width:15px; height:15px; background-color:rgb(66, 133, 244); border-radius:50%; margin-right:5px;"></span> Main Entity</div>
            <div><span style="display:inline-block; width:15px; height:15px; background-color:rgb(52, 168, 83); border-radius:50%; margin-right:5px;"></span> Person</div>
            <div><span style="display:inline-block; width:15px; height:15px; background-color:rgb(66, 197, 244); border-radius:50%; margin-right:5px;"></span> Location</div>
            <div><span style="display:inline-block; width:15px; height:15px; background-color:rgb(251, 188, 5); border-radius:50%; margin-right:5px;"></span> Image</div>
            <div><span style="display:inline-block; width:15px; height:15px; background-color:rgb(234, 67, 53); border-radius:50%; margin-right:5px;"></span> Other</div>
        </div>
    </div>
    
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <script>
    (function() {{
        // Graph data
        const data = {json.dumps(d3_data)};
        
        // D3.js force-directed graph
        const container = document.getElementById('knowledge-graph-container');
        const width = container.clientWidth;
        const height = container.clientHeight;
        
        // Create SVG
        const svg = d3.select('#knowledge-graph-container')
            .append('svg')
            .attr('width', width)
            .attr('height', height)
            .call(d3.zoom().on("zoom", function(event) {{
                svg.attr("transform", event.transform);
            }}))
            .append("g");
        
        // Node color based on type
        const colorMap = {{
            'main': 'rgb(66, 133, 244)',  // Blue
            'person': 'rgb(52, 168, 83)', // Green
            'location': 'rgb(66, 197, 244)', // Light blue
            'image': 'rgb(251, 188, 5)',  // Yellow
            'default': 'rgb(234, 67, 53)' // Red
        }};
        
        // Create force simulation
        const simulation = d3.forceSimulation(data.nodes)
            .force('link', d3.forceLink(data.links).id(d => d.id).distance(150))
            .force('charge', d3.forceManyBody().strength(-300))
            .force('center', d3.forceCenter(width / 2, height / 2))
            .force('collision', d3.forceCollide().radius(60));
        
        // Create links
        const link = svg.append('g')
            .selectAll('path')
            .data(data.links)
            .enter().append('path')
            .attr('stroke', '#999')
            .attr('stroke-opacity', 0.6)
            .attr('stroke-width', 1.5)
            .attr('fill', 'none');
        
        // Create link labels
        const linkText = svg.append('g')
            .selectAll('text')
            .data(data.links)
            .enter().append('text')
            .attr('fill', '#666')
            .attr('font-size', '10px')
            .attr('text-anchor', 'middle')
            .attr('dominant-baseline', 'text-after-edge')
            .attr('dy', -3)
            .text(d => d.label);
        
        // Create nodes
        const node = svg.append('g')
            .selectAll('.node')
            .data(data.nodes)
            .enter().append('g')
            .attr('class', 'node')
            .call(d3.drag()
                .on('start', dragstarted)
                .on('drag', dragged)
                .on('end', dragended));
        
        // Add circles to all nodes
        node.append('circle')
            .attr('r', d => d.type === 'main' ? 25 : 20)
            .attr('fill', d => colorMap[d.type] || colorMap['default'])
            .attr('stroke', '#fff')
            .attr('stroke-width', 2);
        
        // Add images for nodes with image URLs
        node.filter(d => d.image && d.image.startsWith('http'))
            .append('clipPath')
            .attr('id', d => `clip-${{d.id.replace(/[^a-zA-Z0-9]/g, '_')}}`)
            .append('circle')
            .attr('r', 18);
        
        node.filter(d => d.image && d.image.startsWith('http'))
            .append('image')
            .attr('xlink:href', d => d.image)
            .attr('x', -18)
            .attr('y', -18)
            .attr('width', 36)
            .attr('height', 36)
            .attr('clip-path', d => `url(#clip-${{d.id.replace(/[^a-zA-Z0-9]/g, '_')}})`);
        
        // Add text labels
        node.append('text')
            .attr('dy', 30)
            .attr('text-anchor', 'middle')
            .attr('fill', '#333')
            .text(d => d.label)
            .style('font-size', '12px')
            .each(function(d) {{
                const textLength = this.getComputedTextLength();
                if (textLength > 100) {{
                    d3.select(this).text(d.label.substring(0, 12) + '...');
                }}
            }});
        
        // Update positions on each tick
        simulation.on('tick', () => {{
            // Update link paths to create a curved line
            link.attr('d', function(d) {{
                const dx = d.target.x - d.source.x,
                      dy = d.target.y - d.source.y,
                      dr = Math.sqrt(dx * dx + dy * dy);
                return `M${{d.source.x}},${{d.source.y}}A${{dr}},${{dr}} 0 0,1 ${{d.target.x}},${{d.target.y}}`;
            }});
            
            // Update link text positions
            linkText.attr('transform', function(d) {{
                const midX = (d.source.x + d.target.x) / 2;
                const midY = (d.source.y + d.target.y) / 2;
                return `translate(${{midX}},${{midY}})`;
            }});
            
            // Update node positions
            node.attr('transform', d => `translate(${{d.x}},${{d.y}})`);
        }});
        
        // Drag functions
        function dragstarted(event, d) {{
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }}
        
        function dragged(event, d) {{
            d.fx = event.x;
            d.fy = event.y;
        }}
        
        function dragended(event, d) {{
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }}
    }})();
    </script>
    """
    
    return html_content