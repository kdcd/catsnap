<script lang="ts">
  import {Api} from './Api';
  import { navigate } from "svelte-routing";

  let queryInputElement: HTMLTextAreaElement;
  let iso1InputElement: HTMLTextAreaElement;
  let iso2InputElement: HTMLTextAreaElement;
  let geneInputElement: HTMLTextAreaElement;
  let error: string = "";

  async function startSearch(e: Event, database_type: string, search_type: string) {
    let r;
    if (search_type === "accession") {
      r = await Api.searchStart({
        "database_type": database_type,
        "search_type": search_type,
        "query": queryInputElement.value,
      });
    } else if (search_type === "sequence") {
      r = await Api.searchStart({
        "database_type": database_type,
        "search_type": search_type,
        "iso1": iso1InputElement.value, 
        "iso2": iso2InputElement.value, 
        "gene": geneInputElement.value, 
      });
    } else {
      return;
    }
    
    if (r.query_id !== undefined) {
      navigate("/waiting/" + r.query_id);
    } else {
      error = r.error;
    }
  }
  
</script>

<div class="alignment-page">
  <div class="alignment-header">
    <div style="position: absolute; top: 0; display: flex; flex-direction: row; justify-content: flex-end; align-items: center; width: 70%;" > 
      <button class="header-button" style = "background-image: url('/static/icons/icon_help.png');" on:click={() => navigate("/help/")}></button>
      <button class="header-button" style = "background-image: url('/static/icons/icon_contact.png');" on:click={() => navigate("/contacts/")}></button>
    </div>
    <div style = "display: flex; flex-flow: column; align-items: center; justify-content: center; width: 100%; height: 100%;" >
      <h1 class="header-text" style="font-size:45px"><b>CATSNAP</b></h1>
      <h3 class="header-text" style="">online tool searching for conserved alternative proteins</h3>
    </div>
  </div>
  <div class="alignment-content">
    <h2 class="content-text" style="color:#ff006d">{@html error}</h2> 
    <div style="display: flex; flex-direction: row; justify-content: center; align-items: center; height: 100%; width: 100%; padding-bottom: 5%;">
      <div style = "display: flex; flex-flow: column; align-items: center; width: 100%; height: 100%; padding-left: 20%; padding-right: 5%;" >
        <h2 style = "font-family:Arial; width: 100%; font-size: xx-large;">NCBI accession mode</h2>
        <h7 class="input-label">Paste <b>protein</b> accession numbers</h7>
        <h7 class="input-label">(RefSeq/GenBank for plants, RefSeq for animals)</h7>
        <textarea  bind:this={queryInputElement} class="alignment-input" rows="4">NP_565674.1, NP_001189625.1</textarea>
        <div style="display: flex; flex-direction: row; justify-content: center; align-items: center; width: 100%;">
          <button on:click={(e) => startSearch(e, "reduced", "accession")} class="search-button" style = "margin-right:5%">Reduced Database <br> Submit</button>
          <button on:click={(e) => startSearch(e, "full", "accession")} class="search-button" style = "margin-left:5%">Full Database <br> Submit</button>
        </div>
      </div>
      <div style = "display: flex; flex-flow: column; align-items: center; width: 100%; height: 100%; padding-left: 5%; padding-right: 20%;" >
        <h2 style = "font-family:Arial; width: 100%; font-size: xx-large;">Sequence mode</h2>
        <h7 class="input-label">Paste <b>nucleotide</b> sequence of isoform one</h7>
        <h7 class="input-label">(no UTRs, exonic sequences only)</h7>
        <textarea  bind:this={iso1InputElement} class="alignment-input" rows="4">ATGTTGGATCTTAACCTCAACGCTGATTCTCCCGAGTCGACTCAGTACGGTGGTGACTCATACTTAGATCGGCAGACATCAGACAACTCCGCCGGGAATCGAGTGGAAGAGTCCGGTACATCGACGTCGTCAGTTATCAATGCCGATGGAGACGAAGACTCTTGCTCTACTCGAGCTTTCACTCTCAGTTTCGATATTTTAAAAGTCGGAAGTAGTAGCGGCGGAGACGAAAGCCCCGCCGCTTCAGCTTCCGTTACTAAAGAGTTTTTTCCGGTGAGTGGAGACTGTGGACATCTACGAGATGTTGAAGGATCATCAAGCTCTAGAAACTGGATAGATCTTTCTTTTGACCGTATTGGTGACGGAGAAACGAAATTGGTAACTCCGGTTCCGACTCCGGCTCCGGTTCCGGCTCAGGTTAAAAAGAGTCGGAGAGGACCAAGGTCTAGAAGTTCACAGTATAGAGGAGTTACTTTTTATAGAAGAACTGGTCGATGGGAGTCACATATTTGGGATTGTGGGAAACAAGTTTATTTAGGTGGTTTCGACACTGCTCATGCTGCAGCTAGAGCTTATGATCGAGCTGCTATTAAATTTAGAGGTGTTGATGCTGATATCAACTTTACTCTTGGTGATTATGAGGAAGATATGAAACAGGTACAAAACTTGAGTAAGGAAGAGTTTGTGCATATACTGCGTAGACAGAGCACGGGGTTTTCGCGGGGGAGTTCGAAGTATCGAGGGGTTACGTTACACAAATGTGGTAGATGGGAAGCTAGGATGGGGCAGTTTCTTGGTAAAAAGGCTTATGACAAGGCTGCAATCAACACTAATGGTAGAGAAGCAGTCACGAACTTCGAGATGAGTTCATACCAAAATGAGATTAACTCTGAGAGCAATAACTCTGAGATTGACCTCAACTTGGGAATCTCTTTATCGACCGGTAATGCGCCAAAGCAAAATGGGAGGCTCTTTCACTTCCCTTCTAATACTTATGAAACTCAGCGTGGAGTTAGCTTGAGGATAGATAACGAATACATGGGAAAGCCGGTGAATACACCTCTTCCTTATGGATCCTCGGATCATCGCCTTTACTGGAACGGAGCATGCCCGAGTTATAATAATCCCGCCGAGGGAAGAGCAACAGAAAAGAGAAGTGAAGCTGAAGGGATGATGAGTAACTGGGGATGGCAGAGACCGGGGCAAACAAGCGCCGTGAGACCGCAGCCACCGGGACCACAACCACCACCATTGTTCTCAGTTGCAGCAGCATCATCAGGATTCTCACATTTCCGGCCACAACCTCCCAATGACAATGCAACACGTGGTTACTTTTATCCACACCCTTAA</textarea>
        <h7 class="input-label">Paste <b>nucleotide</b> sequence of isoform two</h7>
        <h7 class="input-label">(no UTRs, exonic sequences only)</h7>
        <textarea  bind:this={iso2InputElement} class="alignment-input" rows="4">ATGTTGGATCTTAACCTCAACGCTGATTCTCCCGAGTCGACTCAGTACGGTGGTGACTCATACTTAGATCGGCAGACATCAGACAACTCCGCCGGGAATCGAGTGGAAGAGTCCGGTACATCGACGTCGTCAGTTATCAATGCCGATGGAGACGAAGACTCTTGCTCTACTCGAGCTTTCACTCTCAGTTTCGATATTTTAAAAGTCGGAAGTAGTAGCGGCGGAGACGAAAGCCCCGCCGCTTCAGCTTCCGTTACTAAAGAGTTTTTTCCGGTGAGTGGAGACTGTGGACATCTACGAGATGTTGAAGGATCATCAAGCTCTAGAAACTGGATAGATCTTTCTTTTGACCGTATTGGTGACGGAGAAACGAAATTGGTAACTCCGGTTCCGACTCCGGCTCCGGTTCCGGCTCAGGTTAAAAAGAGTCGGAGAGGACCAAGGTCTAGAAGTTCACAGTATAGAGGAGTTACTTTTTATAGAAGAACTGGTCGATGGGAGTCACATATTTGGGATTGTGGGAAACAAGTTTATTTAGGTGGTTTCGACACTGCTCATGCTGCAGCTAGAGCTTATGATCGAGCTGCTATTAAATTTAGAGGTGTTGATGCTGATATCAACTTTACTCTTGGTGATTATGAGGAAGATATGAAACAGGTACAAAACTTGAGTAAGGAAGAGTTTGTGCATATACTGCGTAGACAGAGCACGGGGTTTTCGCGGGGGAGTTCGAAGTATCGAGGGGTTACGTTACACAAATGTGGTAGATGGGAAGCTAGGATGGGGCAGTTTCTTGGTAAAAAGTATATTTATCTTGGGCTGTTCGACAGCGAAGTAGAAGCTGCAAGGGCTTATGACAAGGCTGCAATCAACACTAATGGTAGAGAAGCAGTCACGAACTTCGAGATGAGTTCATACCAAAATGAGATTAACTCTGAGAGCAATAACTCTGAGATTGACCTCAACTTGGGAATCTCTTTATCGACCGGTAATGCGCCAAAGCAAAATGGGAGGCTCTTTCACTTCCCTTCTAATACTTATGAAACTCAGCGTGGAGTTAGCTTGAGGATAGATAACGAATACATGGGAAAGCCGGTGAATACACCTCTTCCTTATGGATCCTCGGATCATCGCCTTTACTGGAACGGAGCATGCCCGAGTTATAATAATCCCGCCGAGGGAAGAGCAACAGAAAAGAGAAGTGAAGCTGAAGGGATGATGAGTAACTGGGGATGGCAGAGACCGGGGCAAACAAGCGCCGTGAGACCGCAGCCACCGGGACCACAACCACCACCATTGTTCTCAGTTGCAGCAGCATCATCAGGATTCTCACATTTCCGGCCACAACCTCCCAATGACAATGCAACACGTGGTTACTTTTATCCACACCCTTAA</textarea>
        <h7 class="input-label">Paste <b>nucleotide</b> sequence of the gene of origin</h7>
        <h7 class="input-label">(primary transcript)</h7>
        <textarea  bind:this={geneInputElement} class="alignment-input" rows="4">AGTTATTATACACATTTATAGTTACAGAGAGAGAAAAACAACTTTATTATAAATAATGATCATCCTCTAAAATTGGGTCTGAAATGTTCCCTCACACGTCTCCTTCTATCTTCTTCTCCACTTTAAAAAAAAAAAATATCCGTCTCACTCTCTCGCCGCCGGTAACATTTCCCGGCGACAAAACTTCTCTACTCTCACCATTCCTCCATCGTAATCTCTAAATTCTTCTCCATTCTCTTCTTCCTCCCGATCATCTCGAGCTCTTCGTGAGAGATTATGTGATTATGTAATCGTTGTTGCTGTAGAAGACGATCTCTAACAACTGATTCCTTCATCATCACCTTCGCTAGATTTGTAATTTTCAGAGCTTGAGATGTTGGATCTTAACCTCAACGCTGATTCTCCCGAGTCGACTCAGTACGGTGGTGACTCATACTTAGATCGGCAGACATCAGACAACTCCGCCGGGAATCGAGTGGAAGAGTCCGGTACATCGACGTCGTCAGTTATCAATGCCGATGGAGACGAAGACTCTTGCTCTACTCGAGCTTTCACTCTCAGTTTCGATATTTTAAAAGTCGGAAGTAGTAGCGGCGGAGACGAAAGCCCCGCCGCTTCAGCTTCCGTTACTAAAGAGTTTTTTCCGGTGAGTGGAGACTGTGGACATCTACGAGATGTTGAAGGATCATCAAGCTCTAGAAACTGGATAGATCTTTCTTTTGACCGTATTGGTGACGGAGAAACGAAATTGGTAACTCCGGTTCCGACTCCGGCTCCGGTTCCGGCTCAGGTTAAAAAGAGTCGGAGAGGACCAAGGTCTAGAAGTTCACAGTATAGAGGAGTTACTTTTTATAGAAGAACTGGTCGATGGGAGTCACATATTTGGTAAGTTTTTTTTTTTTGTTGTTGATGATAATACAAGTTTCTCGATTTAGTAATTTTTATCAGTGAGATTGATTCAATTTTTTTTTGTTTTGTAGGGATTGTGGGAAACAAGTTTATTTAGGTAAATTACAATTTTTGTTAAAATTTTGATGATTAAGATTATTGATTCATGGTTGTTGATTTATATAGGTGGTTTCGACACTGCTCATGCTGCAGCTAGGTAATTTTTGGATTATTATAGATAAAAGTTTTGTTTTCGGAATTGTTAAGGTTTGGATTTTGATTAGTGTTTGTGTTTTTGTAGAGCTTATGATCGAGCTGCTATTAAATTTAGAGGTGTTGATGCTGATATCAACTTTACTCTTGGTGATTATGAGGAAGATATGAAACAGGTTTTTGGATATAAGTCTTTTGTTTTGGTTATATGATTGTTTTGAGTAGTTTTTTTTTTAACTGTGTTATCTTCTTGTTTAGGTACAAAACTTGAGTAAGGAAGAGTTTGTGCATATACTGCGTAGACAGAGCACGGGGTTTTCGCGGGGGAGTTCGAAGTATCGAGGGGTTACGTTACACAAATGTGGTAGATGGGAAGCTAGGATGGGGCAGTTTCTTGGTAAAAAGTGAGCAATTTTGTTCTTTAATATGAACTTTTTGATTTTAGAAAGGGTATGAAACTAGGAATGGTGTCTAAGTAGTGGTTAGGTGATTAAGATGCTTGAATTGCAGGTATATTTATCTTGGGCTGTTCGACAGCGAAGTAGAAGCTGCAAGGTTCCTTAATGATCATTGTTTGATAGAAACCTTTAGTAGAACTTCACTTTGTTTTTATCAAAGCCAACATGAAGTTTCTTTCTTTCTAAACATTTTCTTGACAACAGGGCTTATGACAAGGCTGCAATCAACACTAATGGTAGAGAAGCAGTCACGAACTTCGAGATGAGTTCATACCAAAATGAGATTAACTCTGAGAGCAATAACTCTGAGATTGACCTCAACTTGGGAATCTCTTTATCGACCGGTAATGCGCCAAAGCAAAATGGGAGGCTCTTTCACTTCCCTTCTAATACTTATGAAACTCAGCGTGGAGTTAGCTTGAGGGTAACTAACTTTCAAATACCAATCTCTCATGAATTCAAAACGTACGTTTCTTATCGTCTTTTAAACAAACTGCAGATAGATAACGAATACATGGGAAAGCCGGTGAATACACCTCTTCCTTATGGATCCTCGGATCATCGCCTTTACTGGAACGGAGCATGCCCGAGTTATAATAATCCCGCCGAGGTAAAAACATAGAATCAAAGTGAAACAACACAATGTAGTCGCAAGACAATGAAACAATGTTTGTTTTTTCAGGGAAGAGCAACAGAAAAGAGAAGTGAAGCTGAAGGGATGATGAGTAACTGGGGATGGCAGAGACCGGGGCAAACAAGCGCCGTGAGACCGCAGCCACCGGGACCACAACCACCACCATTGTTCTCAGTTGCAGCAGCATCATCAGGATTCTCACATTTCCGGCCACAACCTCCCAATGACAATGCAACACGTGGTTACTTTTATCCACACCCTTAACTTGTAAGGGGACATATGAGAGTTTTTTTACCATCTCTCTCTCTCTCAACACTCTAGTCCCCTTTCAAAAATGTCATTTGGGTTTTAGATTTTTCACATACAATGATCAATTTTTCCAAATTCAGATGAGAAAATGTGTTTTTTTTTACATCAAAATTTGGTTTGTTGAGAAAAAACTTTATCAACTAAATGGTAAAAAAAATGTGTATGTTTGTGGTAAATTTTAAATCTTCTCAAAATGTCTTTACCTAATAAGGTTTGTTTATGTGAAAATATGTTTTTTTGGTAAGAGGACTCTTGAAATTTGGAAGGTACAATTTGTAACAAAAAATAAAATATGAGGATGAAGTTTTGTCGTTTTATGTGAAGGTTTGATAGTATAAGATATTTTGATTAAAATAACACTGTTGAAAAGAACAGTAAAGAGAGATAGTGATAGGTTTTGGCTGCCTCTTCGGAACCCCGAAACGATTTGGCAAAAACATTACATTCTTATTTGTATACATATTCGG</textarea>
        <div style="display: flex; flex-direction: row; justify-content: center; align-items: center; width: 100%;">
          <button on:click={(e) => startSearch(e, "reduced", "sequence")} class="search-button" style = "margin-right:5%">Reduced Database <br> Submit</button>
          <button on:click={(e) => startSearch(e, "full", "sequence")} class="search-button" style = "margin-left:5%">Full Database <br> Submit</button>
        </div>
      </div>
    </div>
  </div>
</div>

<style>
  .alignment-page {
    display: flex;
    flex-flow: column;
    height: 100%;
    width: 100%;
  }

  .alignment-header {
    display: flex;
    flex-flow: column;
    align-items: center;
    flex: 0 1 30%;
    background: #59253a;
    width: 100%;
  }

  .header-button {
    margin-right:2px;
    
    padding: 20px 20px;
    text-align: center;
    text-decoration: none;
    display: inline-block;
    font-size: 16px;
    transition-duration: 0.4s;
    cursor: pointer;

    background-image: url("/static/icons/icon_help.png");
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

  .search-button {
      padding: 8px 16px;
      text-align: center;
      text-decoration: none;
      display: block;
      font-size: 16px;
      margin: 15px 0px;
      transition-duration: 0.4s;
      border-radius: 5px;
      cursor: pointer;
      align-self: flex-start;
      width:50%;
      height:70px;

      background-color: white; 
      color: black; 
      border: 2px solid #59253a;
  }

  .search-button:hover {
      background-color: #59253a;
      color: white;
  }

  .header-space-1 {
    flex: 0 1 25%;
  }

  .header-text {
    font-family:Arial;
    display: flex;
    color: #b7a7b1;
    font-weight:normal;
  }

  .header-space-2 {
    flex: 0 1 1%;
  }

  .alignment-content {
    display: flex;
    flex-flow: column;
    flex: 1 1 auto;
    width: 100%;
    /* justify-content: center; */
    align-items: center;
  }
  
  .alignment-content-space-1 {
    flex: 0 1 5%;
  }

  .alignment-content-input-container {
    display: flex;
    flex-flow: column;
    align-items: center;
    width: 100%;
    height: 100%;
    padding-left: 10%;
    padding-right: 10%;

  }

  .input-label {
    width:100%;
    font-family:Arial;
    font-size: 14px;
  }

  .alignment-input {
    width:99%;
    height:100px;

    resize: none;
    border-width: 2px;
    border-radius: 5px;
    border-color: #59253a;
    font-size: 14px;
    margin-bottom: 5px;
    margin-top: 5px;
  }


</style>
