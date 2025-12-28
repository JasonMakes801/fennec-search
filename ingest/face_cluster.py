"""
Face clustering using HDBSCAN from scikit-learn.
Groups similar faces together and assigns cluster_order for UI display.
"""

import numpy as np
from db import get_connection


def cluster_faces():
    """
    Cluster all faces using HDBSCAN.
    Updates cluster_id and cluster_order for each face.
    
    HDBSCAN automatically determines the number of clusters and handles noise.
    - cluster_id: cluster assignment (-1 = noise/unclustered)
    - cluster_order: distance to cluster centroid (lower = more representative)
    """
    conn = get_connection()
    cur = conn.cursor()
    
    # Get all face embeddings - cast to float array for numpy
    cur.execute("""
        SELECT id, embedding::text
        FROM faces
        WHERE embedding IS NOT NULL
        ORDER BY id
    """)
    
    rows = cur.fetchall()
    
    if not rows:
        print("    No faces to cluster")
        cur.close()
        conn.close()
        return
    
    face_ids = [row[0] for row in rows]
    # Parse embedding strings from pgvector format [x,y,z,...] to numpy arrays
    import json
    embeddings = np.array([json.loads(row[1]) for row in rows])
    
    print(f"    Clustering {len(face_ids)} faces...")
    
    # Import here to avoid loading at startup
    from sklearn.cluster import HDBSCAN
    
    # HDBSCAN clustering (using sklearn's built-in implementation)
    # min_cluster_size: minimum faces to form a cluster (2 = pair of same person)
    # min_samples: how conservative clustering should be (lower = more clusters)
    # metric: euclidean for normalized embeddings
    clusterer = HDBSCAN(
        min_cluster_size=2,
        min_samples=1,
        metric='euclidean',  # embeddings are normalized, euclidean works well
        cluster_selection_epsilon=0.0,
        cluster_selection_method='eom'  # excess of mass - good for varying densities
    )
    
    cluster_labels = clusterer.fit_predict(embeddings)
    
    # Count clusters (excluding noise labeled as -1)
    unique_clusters = set(cluster_labels) - {-1}
    num_clusters = len(unique_clusters)
    noise_count = np.sum(cluster_labels == -1)
    
    print(f"    Found {num_clusters} clusters, {noise_count} unclustered faces")
    
    # Calculate centroids and distances for ordering within clusters
    cluster_centroids = {}
    for cluster_id in unique_clusters:
        mask = cluster_labels == cluster_id
        cluster_embeddings = embeddings[mask]
        centroid = cluster_embeddings.mean(axis=0)
        centroid = centroid / np.linalg.norm(centroid)  # normalize
        cluster_centroids[cluster_id] = centroid
    
    # Calculate cluster_order (distance to centroid) for each face
    cluster_orders = []
    for i, (face_id, cluster_id) in enumerate(zip(face_ids, cluster_labels)):
        if cluster_id == -1:
            # Unclustered faces: use large value so they sort last
            cluster_orders.append(999.0)
        else:
            centroid = cluster_centroids[cluster_id]
            # Cosine distance (1 - dot product for normalized vectors)
            dist = 1.0 - np.dot(embeddings[i], centroid)
            cluster_orders.append(float(dist))
    
    # Sort clusters by size (largest first) and remap IDs
    cluster_sizes = {}
    for label in cluster_labels:
        if label != -1:
            cluster_sizes[label] = cluster_sizes.get(label, 0) + 1
    
    # Create mapping from old cluster ID to new (sorted by size)
    sorted_clusters = sorted(cluster_sizes.keys(), key=lambda x: -cluster_sizes[x])
    cluster_remap = {old: new for new, old in enumerate(sorted_clusters)}
    cluster_remap[-1] = -1  # Keep noise as -1
    
    # Update database
    for face_id, old_cluster_id, cluster_order in zip(face_ids, cluster_labels, cluster_orders):
        new_cluster_id = cluster_remap[old_cluster_id]
        cur.execute("""
            UPDATE faces
            SET cluster_id = %s, cluster_order = %s
            WHERE id = %s
        """, (int(new_cluster_id), cluster_order, face_id))
    
    conn.commit()
    cur.close()
    conn.close()
    
    # Print cluster summary
    for new_id, old_id in enumerate(sorted_clusters[:5]):  # Show top 5
        print(f"      Cluster {new_id}: {cluster_sizes[old_id]} faces")
    if len(sorted_clusters) > 5:
        print(f"      ... and {len(sorted_clusters) - 5} more clusters")
    
    print(f"    ✓ Face clustering complete")
