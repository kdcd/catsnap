PREFIX_QUERY = "query_"
PREFIX_HIT = "hit_"
PREFIX_ISOFORM = "isoform_"
PREFIX_CORRECT = "correct_"


def concat(prefix: str, col: str) -> str:
    return prefix + col


def query(col: str) -> str:
    return concat(PREFIX_QUERY, col)


def correct(col: str) -> str:
    return concat(PREFIX_CORRECT, col)


def hit(col: str) -> str:
    return concat(PREFIX_HIT, col)


def isoform(col: str) -> str:
    return concat(PREFIX_ISOFORM, col)


def hit_isoform(col: str) -> str:
    return hit(isoform(col))


def query_isoform(col: str) -> str:
    return query(isoform(col))


def query_hit(col: str) -> str:
    return query(hit(col))


DB_XREF = "db_xref"

FILE = "file"

UUID = "uuid"
ID = "id"
GENE_RECORD_UUID = "gene_record_uuid"
GENE_UUID = "gene_uuid"
GENE = "gene"
GENE_ID = "gene_id"
DESCRIPTION = "description"
PRODUCT = "product"
PROTEIN_ID = "protein_id"
TRANSLATION = "translation"
GENE_SEQUENCE = "gene_sequence"
SEQUENCE_ID = "sequence_id"
GENE_LOCATION = "gene_location"
ISOFORM_LOCATION = "isoform_location"
ISOFORM_UUID = "isoform_uuid"
ISOFORM_SEQUENCE = "isoform_sequence"
ISOFORM_LOCATION_IN_GENE = "isoform_location_in_gene"
SPLICING_ID = "splicing_id"
SPLICING_TUPLE_ID = "splicing_tuple_id"
LOCATION_STATS = "location_stats"
LOCUS_TAG = "locus_tag"
ORGANISM = "organism"
ISOFORMS_FILTER = "isoforms_filter"
ISOFORMS = "isoforms"

QUERY_ISOFORM_UUID = query(ISOFORM_UUID)
HIT_ISOFORM_UUID = hit(ISOFORM_UUID)
HIT_ID = "hit_id"

SCORE = "score"
ORGANISM_SCORE = "organism_score"
ORGANISM_FLANKING_SCORE = "organism_flanking_score"
ORGANISM_SPLICING_SCORE = "organism_splicing_score"
NOT_CONSTANT_HITS = "not_constant_hits"
FLANKING_HITS = "flanking_hits"
NOT_CONSTANT_MAX_LEN = "not_constant_max_len"
NOT_CONSTANT_LEN = "not_constant_len"
FLANKING_LEN = "flanking_len"
ISOFORM_NOT_CONSTANT_LEN = "isoform_not_constant_len"
NOT_CONSTANT_SCORE = "not_constant_score"
FLANKING_SCORE = "flanking_score"
SPLICING_STATUS = "splicing_status"
SPLICING_THRESHOLD = "splicing_threshold"
SPLICING_SCORE = "splicing_score"
SPLICING_SCORE_A = "splicing_score_a"
SPLICING_SCORE_B = "splicing_score_b"
NOT_CONSTANT_RATIO_DIFF = "not_constant_ratio_diff"
NOT_CONSTANT_RATIO_DIFF_A = "not_constant_ratio_diff_a"
NOT_CONSTANT_RATIO_DIFF_B = "not_constant_ratio_diff_b"
SELF_SIMILARITY = "self_similarity"
CONSTANT_SEGMENT_COUNT = "constant_segment_count"
NOT_CONSTANT_SEGMENT_COUNT = "not_constant_segment_count"
SIMILARITY_SCORE = "similarity_score"

PROBABLE_PRODUCT_CONSERVATIVE = "probable_product_conservative"
PROBABLE_FLANKING_CONSERVATIVE = "probable_flanking_conservative"
PROBABLE_SPLICING_CONSERVATIVE = "probable_splicing_conservative"

FLANKING = "flanking"
CONSTANT = "constant"
NOT_CONSTANT = "not_constant"

NOT_CONSTANT_REGION_IDX = "not_constant_regions_count"
REGIONS = "regions"

CLASS = "class"
