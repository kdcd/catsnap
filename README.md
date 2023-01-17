<figure>
  <img src="https://github.com/konovalovdmitry/catsnap/blob/master/picture.PNG" "/>
</figure>

## ABOUT

This repository contains the code of Catsnap – a tool to assess the conservation of alternative splicing. 

Amino acid sequences of alternative proteins, produced by alternatively spliced genes, were downloaded from [RefSeq](https://www.ncbi.nlm.nih.gov/refseq/) and [GenBank](https://www.ncbi.nlm.nih.gov/genbank/) databases.

The user provides the RefSeq or GenBank accession numbers of the canonical and alternative protein isoforms (or their sequencies) and Catsnap [Blasts](https://blast.ncbi.nlm.nih.gov/Blast.cgi) them against its internal database of alternative proteins. The resulting output is then prelimenary organized in pairs of presumably canonical and alternative isoforms. 

Catsnap looks for those prelimenary pairs which share the highest amino acid similarity with the query pair, especially in the regions affected by alternative splicing. This task is carried out by a logistic regression machine learning model, trained on 1,426 instances of conserved alternative splicing events. 

Finally, Catsnap sorts the hit pairs from highest to lowest similarity to the query. Hit pairs with high similarity likely represent conserved alternative splicing events.

The detailed description of the pipeline is provided in the paper "Catsnap: a user-friendly algorithm for determining the conservation of protein variants reveals extensive parallelisms in evolution of alternative splicing " available at ...

The online tool can be found at …

## Requirements

Python>=3.10, at least ~300 GB space, and more than 64 GB RAM

```
cd kd_splicing
pip install -r requirements.txt
```

## How to

Download database source files

```
python -m kd_splicing.database.download_refseq_genome
python -m kd_splicing.database.download_genbank
```

Extract sequence files and build blast and sqllite db

```
python -m kd_splicing.database.extract
```

Make single search request

```

from kd_splicing import ml, helpers, pipeline,
from kd_splicing.database import filedb

p = pipeline.get_test_pipeline()

file_db = filedb.FileDB.create(FILE_DB_PATH)
detector = ml.Detector.load(DETECTOR_PATH)
helpers.search(file_db, p, detector, ["NP_200130.1, NP_001078750.1"], blast_db, isoforms_to_duplicates=file_db.isoform_to_duplicates)
```

Start svelte frontend

```
npm run dev
```


## CITATION

If you find our work useful, please cite ...
