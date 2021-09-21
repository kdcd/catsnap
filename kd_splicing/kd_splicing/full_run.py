from kd_splicing import blast, features, full, ml, paths, pipeline, database, helpers
from kd_common import pathutil
import pickle
import os
import scikitplot as skplt

def create_blast_db_with_duplicates():
    p = pipeline.get_test_pipeline("full")
    db = database.store.read(p.db_merged_store_path)
    blast.create_db(db, paths.PATH_BLAST_DB_WITH_DUPLICATES, deduplicate_isoforms=False)

def main() -> None:
    timestamp = "2021_02_16_17_37_56"
    p = pipeline.get_test_pipeline("full_" + timestamp)
    store_folder = os.path.join(paths.FOLDER_STORES, timestamp)
    blast_db_folder = pathutil.create_folder(store_folder, "blast_db")
    blast_db_path = os.path.join(blast_db_folder, "db")
    detector_path = os.path.join(paths.FOLDER_DATA, "detector.pkl")
    num_groups = 18
    
    db = database.store.read(os.path.join(store_folder, "store_merged.pkl"))
    queries = full.get_query_isoforms(db, num_groups)
    blast.create_db(db, blast_db_path)
    blast.create_queires(db, queries, p.launch_folder)

    # blast.run(p.launch_folder, blast_db_path, num_groups=num_groups)

    db = database.store.read(os.path.join(store_folder, "store_merged.pkl"))
    queries = full.get_query_isoforms(db, num_groups)
    queries.isoform_to_file = helpers.get_isoforms_to_file(p.launch_folder)
    detector = ml.Detector.load(detector_path)
    features.calc_parallel(db, p.launch_folder, queries, queries.tuples, detector)


if __name__ == "__main__":
    # create_blast_db_with_duplicates()
    main()