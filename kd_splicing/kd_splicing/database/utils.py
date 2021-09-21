import uuid
from kd_splicing.database.models import DB
from typing import Mapping, Dict, List
from collections import defaultdict
import pandas as pd
from tqdm import tqdm


def get_gene_to_isoforms(db: DB) -> Mapping[uuid.UUID, List[uuid.UUID]]:
    gene_to_isoforms: Dict[uuid.UUID, List[uuid.UUID]] = defaultdict(list)
    for isoform in db.isoforms.values():
        gene_to_isoforms[isoform.gene_uuid].append(isoform.uuid)

    return gene_to_isoforms

def to_df(db: DB) -> pd.DataFrame:
    data = []
    for iso in tqdm(db.isoforms.values()):
        gene = db.genes[iso.gene_uuid]
        record = db.records[gene.record_uuid]
        f = db.files[record.file_uuid]
        
        row = {
            "isoform_uuid": iso.uuid,
            "protein_id": iso.protein_id,
            "product": iso.product,
            "gene_uuid": gene.uuid,
            "locus_tag": gene.locus_tag,
            "gene_id": gene.gene_id,
            "db_xref": gene.db_xref,
            "organism": record.organism,
            "sequence_id": record.sequence_id,
            "gb_file": f.src_gb_file,
            "db_name": f.db_name,
            "db_name_src": f.db_name,
        }
        if iso.src_gene_uuid:
            row["db_name_src"] = "genbank"
        if iso.src_gene_uuid and iso.src_gene_uuid in db.genes:
            src_gene = db.genes[iso.src_gene_uuid]
            src_record = db.records[src_gene.record_uuid]
            src_f = db.files[src_record.file_uuid]
            row = {
                **row,
                "src_locus_tag": src_gene.locus_tag,
                "src_gene_id": src_gene.gene_id,
                "src_organism": src_record.organism,
                "src_db_name": src_f.db_name,
            }

        data.append(row)
    return pd.DataFrame(data)


