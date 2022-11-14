<figure>
  <img src="https://github.com/konovalovdmitry/catsnap/blob/master/images/picture.png" />
</figure>

## ABOUT

This repository contains the code of Catsnap – a tool to assess the conservation of alternative splicing. 

Amino acid sequences of alternative proteins, produced by alternatively spliced genes, were downloaded from [RefSeq](https://www.ncbi.nlm.nih.gov/refseq/) and [GenBank](https://www.ncbi.nlm.nih.gov/genbank/) databases.

The user provides the RefSeq or GenBank accession numbers of the canonical and alternative protein isoforms (or their sequencies) and Catsnap [Blasts](https://blast.ncbi.nlm.nih.gov/Blast.cgi) them against its internal database of alternative proteins. The resulting output is then prelimenary organized in pairs of presumably canonical and alternative isoforms. 

Catsnap looks for those prelimenary pairs which share the highest amino acid similarity with the query pair, especially in the regions affected by alternative splicing. This task is carried out by a logistic regression machine learning model, trained on 1,426 instances of conserved alternative splicing events. 

Finally, Catsnap sorts the hit pairs from highest to lowest similarity to the query. Hit pairs with high similarity likely represent conserved alternative splicing events.

The detailed description of the pipeline is provided in the paper "Catsnap: a user-friendly algorithm for determining the conservation of protein variants reveals extensive parallelisms in evolution of alternative splicing " available at ...

The online tool can be found at …

## CITATION

If you find our work useful, please cite ...
