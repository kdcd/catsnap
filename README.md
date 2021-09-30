<figure>
  <img src="https://github.com/konovalovdmitry/catsnap/blob/master/images/picture.png" />
</figure>

## ABOUT

This repository contains the code of Catsnap – a tool to assess the conservation of alternative splicing in plants. 

Amino acid sequences of alternative proteins, produced by alternatively spliced genes, were downloaded from [RefSeq](https://www.ncbi.nlm.nih.gov/refseq/) and [GenBank](https://www.ncbi.nlm.nih.gov/genbank/) databases.

The user provides the RefSeq or GenBank accession numbers of the canonical and alternative plant protein isoforms and Catsnap [Blasts](https://blast.ncbi.nlm.nih.gov/Blast.cgi) them against its database of alternative proteins. The resulting output is then organized in pairs of presumably canonical and alternative isoforms similarly to the entered query pair. 

Among the formed hit pairs Catsnap looks for those which share the highest amino acid similarity with the query pair, especially in the regions affected by alternative splicing. This task is carried out by a logistic regression machine learning model, trained on 1,426 instances of conserved alternative splicing events. 

Finally, Catsnap sorts the hit pairs from highest to lowest similarity to the query. Hit pairs with high similarity likely represent conserved alternative splicing events.

The detailed description of the pipeline is provided in the paper "Catsnap: a user-friendly algorithm for determining the conservation of plant splice variants reveals extensive parallelisms in protein isoform evolution" available at ...

The online tool can be found at …

## CITATION

If you find our work useful, please cite ...
