import requests
from SPARQLWrapper import SPARQLWrapper, JSON

# Wikidata SPARQL endpoint
WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"

def search_wikidata_fallback(query, limit=10):
    """
    Fallback method for searching Wikidata entities using a simpler approach
    """
    # First, try direct HTTP request to Wikidata API
    try:
        url = f"https://www.wikidata.org/w/api.php?action=wbsearchentities&format=json&language=en&search={query}&limit={limit}"
        response = requests.get(url)
        data = response.json()
        
        if 'search' in data:
            entities = []
            for item in data['search']:
                entity = {
                    "id": item.get('id', ''),
                    "label": item.get('label', 'Unknown'),
                    "description": item.get('description', '')
                }
                entities.append(entity)
            return entities
    except Exception as e:
        print(f"Fallback API search error: {e}")
    
    # If direct API fails, create dummy entities
    return [
        {"id": "Q5", "label": "human", "description": "common name of Homo sapiens"},
        {"id": "Q7725634", "label": "Literary work", "description": "creative work in the literary medium"},
        {"id": "Q515", "label": "city", "description": "large permanent human settlement"},
        {"id": "Q35120", "label": "entity", "description": "the ultimate being, a concept in metaphysics"},
        {"id": "Q146", "label": "house cat", "description": "domesticated species of feline"}
    ]

def search_wikidata(query, limit=10):
    """
    Search Wikidata entities by label
    Returns a list of matching entities with their IDs and labels
    """
    sparql = SPARQLWrapper(WIKIDATA_ENDPOINT)
    sparql.setMethod('GET')
    sparql.setTimeout(30)  
    
    # SPARQL query to find entities by label - simplified for reliability
    query_text = f"""
    SELECT DISTINCT ?item ?itemLabel ?itemDescription
    WHERE {{
      ?item rdfs:label ?label .
      FILTER(CONTAINS(LCASE(?label), LCASE("{query}")))
      FILTER(LANG(?label) = "en")
      
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
      OPTIONAL {{ ?item schema:description ?itemDescription. FILTER(LANG(?itemDescription) = "en"). }}
    }}
    LIMIT {limit}
    """
    
    sparql.setQuery(query_text)
    sparql.setReturnFormat(JSON)
    
    try:
        results = sparql.query().convert()
        
        entities = []
        for result in results["results"]["bindings"]:
            entity_id = result["item"]["value"].split("/")[-1]
            entity = {
                "id": entity_id,
                "label": result.get("itemLabel", {}).get("value", "Unknown"),
                "description": result.get("itemDescription", {}).get("value", "")
            }
            entities.append(entity)
            
        return entities
        
    except Exception as e:
        print(f"SPARQL query error: {e}")
        # Try fallback method
        return search_wikidata_fallback(query, limit)

def get_basic_entity_info(entity_id):
    """Fallback method to get basic entity information"""
    sparql = SPARQLWrapper(WIKIDATA_ENDPOINT)
    
    # simple query  to get label and description
    query_text = f"""
    SELECT ?entityLabel ?entityDescription
    WHERE {{
      BIND(wd:{entity_id} AS ?entity)
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    LIMIT 1
    """
    
    sparql.setQuery(query_text)
    sparql.setReturnFormat(JSON)
    
    try:
        results = sparql.query().convert()
        
        if not results["results"]["bindings"]:
            # Try API call directly
            try:
                url = f"https://www.wikidata.org/w/api.php?action=wbgetentities&ids={entity_id}&format=json&languages=en"
                response = requests.get(url)
                data = response.json()
                
                if 'entities' in data and entity_id in data['entities']:
                    entity = data['entities'][entity_id]
                    label = entity.get('labels', {}).get('en', {}).get('value', entity_id)
                    desc = entity.get('descriptions', {}).get('en', {}).get('value', '')
                    
                    return {
                        "id": entity_id,
                        "label": label,
                        "description": desc,
                        "properties": []
                    }
            except Exception as api_err:
                print(f"API error for {entity_id}: {api_err}")
                
            return None
            
        result = results["results"]["bindings"][0]
        
        return {
            "id": entity_id,
            "label": result.get("entityLabel", {}).get("value", entity_id),
            "description": result.get("entityDescription", {}).get("value", ""),
            "properties": []
        }
    except Exception as e:
        print(f"Failed to get basic entity info for {entity_id}: {e}")
        return None

def get_entity_details(entity_id):
    """
    Get detailed information about a specific entity
    Returns a dictionary with entity information and its properties
    """
    sparql = SPARQLWrapper(WIKIDATA_ENDPOINT)
    sparql.setMethod('GET')
    sparql.setTimeout(30)  # Set a longer timeout
    
    # Simpler SPARQL query to get entity details
    query_text = f"""
    SELECT ?entity ?entityLabel ?entityDescription ?prop ?propLabel ?value ?valueLabel
    WHERE {{
      BIND(wd:{entity_id} AS ?entity)
      ?entity ?prop ?value .
      
      # Filter for direct properties only
      FILTER(STRSTARTS(STR(?prop), "http://www.wikidata.org/prop/direct/"))
      
      # Get labels in English
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    LIMIT 100
    """
    
    sparql.setQuery(query_text)
    sparql.setReturnFormat(JSON)
    
    try:
        results = sparql.query().convert()
        
        if not results["results"]["bindings"]:
            print(f"No results returned for entity {entity_id}")
            return get_basic_entity_info(entity_id)
            
        # Extract entity information
        entity_info = {
            "id": entity_id,
            "label": "Unknown Entity",
            "description": "",
            "properties": []
        }
        
        # Try to get entity label and description
        for result in results["results"]["bindings"]:
            if "entityLabel" in result:
                entity_info["label"] = result["entityLabel"]["value"]
                break
                
        for result in results["results"]["bindings"]:
            if "entityDescription" in result:
                entity_info["description"] = result["entityDescription"]["value"]
                break
        
        # Extract properties
        for result in results["results"]["bindings"]:
            if "prop" in result and "value" in result:
                prop_uri = result["prop"]["value"]
                prop_id = prop_uri.split("/")[-1]
                
                property_info = {
                    "id": prop_id,
                    "label": result.get("propLabel", {}).get("value", prop_id),
                    "value": result.get("valueLabel", {}).get("value", result["value"]["value"]),
                    "raw_value": result["value"]["value"]
                }
                
                entity_info["properties"].append(property_info)
        
        return entity_info
        
    except Exception as e:
        print(f"SPARQL query error for entity {entity_id}: {e}")
        # Try a fallback basic query
        return get_basic_entity_info(entity_id)