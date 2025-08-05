import osmnx as ox
import networkx as nx
import numpy as np
import geopandas as gpd

ANALYSIS_RADIUS_METERS = 400

def analyze_stop_accessibility(lat, lon):
    
    try:
        point = (lat, lon)
        graph = ox.graph_from_point(point, dist=ANALYSIS_RADIUS_METERS, network_type='walk')

        components = nx.strongly_connected_components(graph)
        largest_component = max(components, key=len)
        graph = graph.subgraph(largest_component).copy()
        nodes = ox.graph_to_gdfs(graph, edges=False)

        for u, v, key, data in graph.edges(keys=True, data=True):
            cost = data['length']
            
            if data.get('highway') == 'steps':
                cost = np.inf
            elif data.get('highway') in ['residential', 'tertiary', 'secondary', 'primary'] and data.get('sidewalk') in ['no', 'none']:
                cost *= 2.0 
            
            if 'kerb' in nodes.columns and nodes.loc[v]['kerb'] not in ['lowered', 'flush']:
                cost *= 1.5

            graph.edges[u, v, key]['accessibility_cost'] = cost

        start_node = ox.nearest_nodes(graph, X=lon, Y=lat)
        accessible_subgraph = nx.ego_graph(
            graph, start_node, radius=ANALYSIS_RADIUS_METERS, distance='accessibility_cost'
        )
        
        accessible_nodes_gdf = ox.graph_to_gdfs(accessible_subgraph, edges=False)
        if accessible_nodes_gdf.empty:
             raise ValueError("No accessible nodes found.")

        accessible_polygon = accessible_nodes_gdf.union_all().convex_hull
        
        gdf_poly = gpd.GeoDataFrame(geometry=[accessible_polygon], crs="EPSG:4326")
        utm_crs = gdf_poly.estimate_utm_crs()
        accessible_polygon_proj = gdf_poly.to_crs(utm_crs).iloc[0].geometry
        
        reachable_area_sq_meters = accessible_polygon_proj.area

        ideal_circular_area = np.pi * (ANALYSIS_RADIUS_METERS ** 2)
        isolation_index = reachable_area_sq_meters / ideal_circular_area if ideal_circular_area > 0 else 0

        total_path_length_km = sum(d['length'] for u, v, d in graph.edges(data=True)) / 1000
        barrier_count = sum(1 for u, v, d in graph.edges(data=True) if d.get('accessibility_cost', 0) == np.inf)
        barrier_density = barrier_count / total_path_length_km if total_path_length_km > 0 else 0

        return {
            "reachable_area": round(reachable_area_sq_meters, 2),
            "isolation_index": round(isolation_index, 3),
            "barrier_density": round(barrier_density, 3),
            "error": None
        }

    except Exception as e:
        return {
            "reachable_area": 0,
            "isolation_index": 0,
            "barrier_density": 0,
            "error": str(e)
        }
    

