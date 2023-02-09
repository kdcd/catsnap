<figure>
  <img src="https://github.com/konovalovdmitry/catsnap/blob/master/picture.PNG" "/>
</figure>

## About

This repository contains the code of Catsnap – a tool for assessing the conservation of alternative splicing (AS).

The amino acid sequences of alternative proteins produced by AS were downloaded from [RefSeq](https://www.ncbi.nlm.nih.gov/refseq/) and [GenBank](https://www.ncbi.nlm.nih.gov/genbank/) databases.

The user provides the RefSeq or GenBank accession numbers of two protein isoforms (or their nucleotide sequences), and Catsnap [blasts](https://blast.ncbi.nlm.nih.gov/Blast.cgi) them against its internal database of alternative proteins. The resulting output is then temporarily organized in pairs to be compared to the query.

Catsnap looks for those temporary pairs which share the highest amino acid similarity with the query pair, especially in the regions affected by alternative splicing. This task is carried out by a logistic regression machine learning model trained on 1,426 instances of the conserved plant AS events.

Finally, Catsnap sorts the hit pairs by similarity to the query sequences. Hit pairs with a high similarity likely represent conserved alternative isoforms.

A detailed description of the pipeline is provided in the publication: Timofeyenko K, Konovalov D, Alexiou P, Kalyna M, Růžička K. Catsnap: a user-friendly algorithm for determining the conservation of protein variants reveals extensive parallelisms in the evolution of alternative splicing, https://doi.org/10.1111/nph.18799.

The online version of the tool can be found at catsnap.cesnet.cz. 

## Requirements

Python>=3.10, at least ~300 GB space, and more than 64 GB RAM

```
cd kd_splicing
pip install -r requirements.txt
```

## Prepare environment

Download database source files

```
python -m kd_splicing.database.download_refseq_genome
python -m kd_splicing.database.download_genbank
```

Extract sequence files and build blast and internal file index

```
python -m kd_splicing.database.extract
```
## How to

Make single ncbi accession mode search request.  Results will be written into kd_splicing/data/ folder

```

from kd_splicing import ml, helpers, pipeline,
from kd_splicing.database import filedb

p = pipeline.get_test_pipeline()

file_db = filedb.FileDB.create(FILE_DB_PATH)
detector = ml.Detector.load(DETECTOR_PATH)
helpers.search(file_db, p, detector, ["NP_200130.1, NP_001078750.1"], BLAST_DB, isoforms_to_duplicates=file_db.isoform_to_duplicates)
```
                                                                   
Make single sequence mode search request

```

helpers.search_custom(file_db, p, detector, gene_seq = GENE_SEQ, iso1_seq = ISO1_SEQ, iso2_seq = ISO2_SEQ, blast_db_path = BLAST_DB)

```
                                                                   
Whole genome search. Depending on hardware can take a lot of time
```
python -m kd_splicing.full_run                                                            

```
                                                                   
## Key files

* Extracting ncbi archive files [kd_splicing.database.archive](https://github.com/kdcd/catsnap/blob/master/kd_splicing/kd_splicing/database/archive.py)
* Running BLAST [kd_splicing.blast](https://github.com/kdcd/catsnap/blob/master/kd_splicing/kd_splicing/blast.py)
* Calculating ml features [kd_splicing.features](https://github.com/kdcd/catsnap/blob/master/kd_splicing/kd_splicing/features.py)                                       
* Writing results [kd_splicing.dump](https://github.com/kdcd/catsnap/blob/master/kd_splicing/kd_splicing/dump.py)
                                                                   
## CITATION

If you find our work useful, please cite ...
