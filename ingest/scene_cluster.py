"""
Scene clustering using HDBSCAN from scikit-learn.
Groups visually similar scenes together using CLIP embeddings.
"""

import numpy as np
from db import get_connection


def cluster_scenes():
    """
    Cluster all scenes using HDBSCAN on CLIP embeddings.
    Updates clip_cluster_id and clip_cluster_order for each scene.

    HDBSCAN automatically determines the number of clusters and handles noise.
    - clip_cluster_id: cluster assignment (-1 = noise/unclustered)
    - clip_cluster_order: distance to cluster centroid (lower = more representative)
    """
    conn = get_connection()
    cur = conn.cursor()

    # Get all CLIP embeddings - cast to float array for numpy
    cur.execute("""
        SELECT s.id, e.embedding::text
        FROM scenes s
        JOIN embeddings e ON s.id = e.scene_id
        WHERE e.model_name = 'clip' AND e.embedding IS NOT NULL
        ORDER BY s.id
    """)

    rows = cur.fetchall()

    if not rows:
        print("    No scenes with CLIP embeddings to cluster")
        cur.close()
        conn.close()
        return

    scene_ids = [row[0] for row in rows]
    # Parse embedding strings from pgvector format [x,y,z,...] to numpy arrays
    import json
    embeddings = np.array([json.loads(row[1]) for row in rows])

    print(f"    Clustering {len(scene_ids)} scenes...")

    # Import here to avoid loading at startup
    from sklearn.cluster import HDBSCAN

    # HDBSCAN clustering (using sklearn's built-in implementation)
    # min_cluster_size: minimum scenes to form a cluster (2 = pair of similar scenes)
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

    print(f"    Found {num_clusters} scene clusters, {noise_count} unclustered scenes")

    # Calculate centroids and distances for ordering within clusters
    cluster_centroids = {}
    for cluster_id in unique_clusters:
        mask = cluster_labels == cluster_id
        cluster_embeddings = embeddings[mask]
        centroid = cluster_embeddings.mean(axis=0)
        centroid = centroid / np.linalg.norm(centroid)  # normalize
        cluster_centroids[cluster_id] = centroid

    # Calculate clip_cluster_order (distance to centroid) for each scene
    cluster_orders = []
    for i, (scene_id, cluster_id) in enumerate(zip(scene_ids, cluster_labels)):
        if cluster_id == -1:
            # Unclustered scenes: use large value so they sort last
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
    for scene_id, old_cluster_id, cluster_order in zip(scene_ids, cluster_labels, cluster_orders):
        new_cluster_id = cluster_remap[old_cluster_id]
        cur.execute("""
            UPDATE scenes
            SET clip_cluster_id = %s, clip_cluster_order = %s
            WHERE id = %s
        """, (int(new_cluster_id), cluster_order, scene_id))

    conn.commit()
    cur.close()
    conn.close()

    # Print cluster summary
    for new_id, old_id in enumerate(sorted_clusters[:5]):  # Show top 5
        print(f"      Cluster {new_id}: {cluster_sizes[old_id]} scenes")
    if len(sorted_clusters) > 5:
        print(f"      ... and {len(sorted_clusters) - 5} more clusters")

    print(f"    Scene clustering complete")
