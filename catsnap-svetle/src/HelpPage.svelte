<script lang="ts">
    import { navigate } from "svelte-routing";

</script>

<style>
  .help-page {
    display: flex;
    flex-flow: column;
    height: 100%;
    width: 100%;
  }

  .help-header {
    font-family:Arial;
    display: flex;
    flex-flow: column;
    align-items: center;
    flex: 1 0 90px;
    background: #59253a;
    width: 100%;
    color: white;
  }

  .help-header-text {
    /* padding:0px;
    margin:10px; */
    color: #b7a7b1;
    align-items: center;
    justify-content: center; 
  }
  
  .help-content {
    font-family:Arial;
    width: 70%;
    display: block;
    flex: 1 0 92%;
    padding: 60px;
    white-space: initial;
  }

  .img {
    display: block;
    padding: 30px;
  }

  .header-button {
    /* position: absolute;
    right: 20%;
    top: 0; */

    margin-right:2px;
    
    padding: 20px 20px;
    text-align: center;
    text-decoration: none;
    display: inline-block;
    font-size: 16px;
    transition-duration: 0.4s;
    cursor: pointer;

    background-image: url("/static/icons/icon_home.png");
    background-repeat: no-repeat;
    background-size: contain;

    background-color: #59253a; 
    color: white; 
    border: none;
  }

  .header-button:hover {
      transform: translateY(4px);
      /* background-color: white; */
      /* color: black; */
  }

</style>

<div class="help-page">
  <div class="help-header"> 
    <h1 class="help-header-text">Instructions</h1>
    <div style="position: absolute; top: 0; display: flex; flex-direction: row; justify-content: flex-end; align-items: center; width: 70%;" > 
      <button class="header-button" style = "background-image: url('/static/icons/icon_home.png');" on:click={() => navigate("/")}></button>
      <button class="header-button" style = "background-image: url('/static/icons/icon_contact.png');" on:click={() => navigate("/contacts/")}></button>
    </div>
  </div>
  <div class="help-content">
    Catsnap uses the submitted pair of sequences corresponding to the alternative splicing event to find similar protein pairs in other species.
    <h2>The NCBI accession mode input</h2>
    A pair of alternative proteins is submitted as RefSeq/GenBank (plants) or RefSeq (animals) protein accession numbers separated by a comma. 
    Here is one of the ways how to find these protein accession numbers in RefSeq:
    <ol>
      <li>Go to https://www.ncbi.nlm.nih.gov/gene/ and find your gene of interest. For example, gene name or AGI locus identifier can be used. 
        <img class="img" src="/static/input1.png" alt="input" width="100%" >
      </li>
      <li>The gene report contains the section “Genomic regions, transcripts, and products” where the gene is displayed graphically by the NCBI Sequence Viewer. A left click on the green gene diagram unfolds available alternative isoforms for mRNA (purple) and protein (red) (follow red arrows).
        <img class="img" src="/static/input2.png" alt="input" width="100%" >
      </li>
      <li>The protein accession number can be copied to the clipboard from the tooltip, which pops up after hovering the mouse over the corresponding protein diagram for a few moments.
        <img class="img" src="/static/input3.png" alt="input" width="100%" >
      </li>
      <li>Paste the copied accession numbers separated by a comma in the Catsnap query field.</li>
    </ol> 
    <h4 id = "accession_troubleshooting">Troubleshooting:</h4>
    <ol>
      <li>Make sure the entered numbers are PROTEIN accession numbers, not mRNA or genes.</li>
      <li>If the entered accession number is correct, but such accession cannot be found in the internal Catsnap library, it is possible that the RefSeq/GenBank databases have been updated in the meanwhile. In such a case, please use the search in the sequence mode.</li>
      <li>If you still experience difficulties, please contact catsnap.help@gmail.com.</li>
    </ol>

    <h2>Multiple queries input in the NCBI accession mode</h2>
    Each query pair must be entered on a new line. Queries can be copied and pasted from an Excel file or any text editor. 
    <img class="img" src="/static/input multiple.png" alt="input" width="50%" >

    <h2>The the sequence mode input</h2>
    You can also perform the search with user-provided sequences. Three sequences must be provided:
    <ol>
      <li>the NUCLEOTIDE sequence of the isoform one,</li>
      <li>the NUCLEOTIDE sequence of the isoform two,</li>
      <li>the NUCLEOTIDE sequence of their gene of origin.</li>
  </ol> 
    Isoform sequences must contain only protein-coding regions lacking 5’- and 3’-untranslated regions and introns.<br>
    Gene sequence must contain exons and introns, the presence of 5’-, 3’-untranslated regions does not matter.<br>
    Catsnap accepts plain sequences, as well as those containing spaces and digits, filtering everything except A, T, G and C:
    <img class="img" src="/static/var1.PNG" alt="input" width="80%" >
   
    <h4 id = "custom_sequence_troubleshooting">Troubleshooting:</h4>
    <ol>
      <li>Make sure that the NUCLEOTIDE sequences are entered.</li>
      <li>The error notification "One of the entered sequences is too long" may arise when very long animal genes are entered. For its work, Catsnap needs to know the positions of exon boundaries in the isoforms. In the sequence mode, exon boundaries are found when isoforms are aligned within the gene sequence by the MUSCLE alignment tool. In the resulting alignment, the exonic sequences of the isoforms and the gene are grouped together, interrupted by the gene introns. The alignment of very long sequences may fail. In such a case, since we are only intrested in the positions of the introns and their nucleotide sequence doesn't matter, the user can shorten the gene length by partial removal of the intronic sequences of the gene.</li> 
      <li>If you still have difficulties, please contact us at catsnap.help@gmail.com.</li>
    </ol>
            
    <h2>Output</h2>
    Catsnap returns similar protein pairs found in other species as amino acid sequences in FASTA format listed in descending order according to their similarity scores. The similarity score values fall in the range between 0 and 1, where 1 means complete identity. 
    Text files with results can be downloaded by clicking the button "Download Results" <img src="/static/icons/icon_download_results.png" alt="input" width="30px" >, 
    which is going to download two text files per query:
    <ol>
      <li>All hits in a species – contains all identified similar protein pairs in a species.</li>
      <li>Best hits in a species – contains only a single pair with the highest similarity score per species. This file is available for an immediate alignment on the output page by clicking the button “Align” <img src="/static/icons/icon_align.png" alt="input" width="30px" >. 
      The alignment is performed by the MUSCLE algorithm.</li>
    </ol> 
    Otherwise, the downloaded FASTA files can be aligned in any alignment tool.

    <h2>Online alignment tool</h2>
    The simple alignment tool allows basic sequence handling as:  
    <ol>
      <li>Deleting unwanted sequences – left click on the sequence name (the name becomes highlighted) and press “delete” on the keyboard;</li>
      <li>Moving sequences up and down within the list – left click on the sequence name and hold to drag to a new position;</li>
      <li>Realignment of the sequences – click “Align” <img src="/static/icons/icon_align.png" alt="input" width="30px" >, when another alignment is needed;</li>
      <li>Editing of the column with names – double left click on the sequence name;</li>
      <li>Saving the alignment by clicking the button "Save Alignment" <img src="/static/icons/icon_save.png" alt="input" width="30px" >.</li>
    </ol> 

    <h2>Multiple queries output</h2>
    Switching between results is carried out through the drop-down menu in the upper left corner where the names of the current gene and pairs are displayed:
    <img class="img" src="/static/multiple switching.png" alt="input" width="30%" >
    Clicking the button <img src="/static/icons/icon_download_results.png" alt="input" width="30px" > downloads the results for all queries at once.
    Clicking the button <img src="/static/icons/icon_save.png" alt="input" width="30px" > downloads the displayed alignment.

    <h2>Help</h2>
    Should you have any difficulties or comments while using Catsnap, please contact us at catsnap.help@gmail.com. 
    This site has been created to make Catsnap available for a broad biological community, and we will be happy to assist you with using it. 
  
    <h2>Using and citing Catsnap</h2>
    Timofeyenko K, Konovalov D, Alexiou P, Kalyna M, Růžička K. Catsnap: a user-friendly algorithm for determining the conservation of protein variants reveals extensive parallelisms in the evolution of alternative splicing, <em>unpublished.</em><br>
    The code is available at https://github.com/kdcd/catsnap.<br>
    <br>
    Please do not use the algorithm without permission prior to its publishing! 





  </div>
</div>

