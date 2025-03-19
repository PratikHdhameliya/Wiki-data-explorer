from flask import Flask, render_template, request, jsonify
from services.sparql_service import search_wikidata, get_entity_details
from services.graph_service import generate_knowledge_graph
import networkx as nx
import json

app = Flask(__name__)

@app.route('/')
def index():
    """Render the search page"""
    return render_template('index.html')

@app.route('/search')
def search():
    """Handle search requests"""
    query = request.args.get('q', '')
    if not query:
        return render_template('results.html', results=[])
    
    results = search_wikidata(query)
    return render_template('results.html', results=results, query=query)

@app.route('/entity/<entity_id>')
def entity(entity_id):
    """Display entity details and visualization"""
    if not entity_id.startswith('Q'):
        # Check if it's a valid numeric ID
        if entity_id.isdigit():
            entity_id = f"Q{entity_id}"
        else:
            # If it contains a namespace (like wdt:P31), extract just the ID
            if ":" in entity_id:
                entity_id = entity_id.split(":")[-1]
    
    # Get entity details using SPARQL
    entity_data = get_entity_details(entity_id)
    
    if not entity_data:
        return render_template('entity.html', error=f"Entity {entity_id} not found", entity=None)
    
    # Generate knowledge graph visualization
    try:
        graph_data = generate_knowledge_graph(entity_id)
        
        # Use the function to generate HTML for the 3D graph
        from services.graph_service import generate_3d_graph_html
        graph_html = generate_3d_graph_html(graph_data)
    except Exception as e:
        print(f"Error generating graph: {e}")
        graph_data = {"nodes": [], "links": []}
        graph_html = None
    
    return render_template(
        'entity.html',
        entity=entity_data,
        graph_data=json.dumps(graph_data) if graph_data else "{}",
        graph_html=graph_html
    )

if __name__ == '__main__':
    app.run(debug=True)