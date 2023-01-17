<script lang="ts">
  import { Api } from "./Api";
  import Cell from "./Cell.svelte";
  import type { Results, ResultsQuery } from "./Models";
  import { navigate } from "svelte-routing";
  import { onMount } from 'svelte';

  export let id;

  let color_map = new Map<string | undefined, string>([
    ["yellow", "#ffee52"],
    ["red", "#f46060"],
    ["green", "#3cc63c"],
    ["purple", "#b652f7"],
    ["blue", "#55d7ff"],
    ["sky", "#61f8ff"],
    ["grassy", "#b9ff55"],
    ["gray", "#d3d385"],
    ["white", "#ffffff"],
  ]);

  let background_color = new Map([
    ["-", "white"],
    ["A", "yellow"],
    ["R", "blue"],
    ["C", "gray"],
    ["N", "green"],
    ["D", "red"],
    ["M", "yellow"],
    ["E", "red"],
    ["T", "green"],
    ["S", "green"],
    ["G", "purple"],
    ["L", "yellow"],
    ["V", "yellow"],
    ["I", "yellow"],
    ["K", "blue"],
    ["P", "blue"],
    ["Y", "grassy"],
    ["Q", "green"],
    ["W", "green"],
    ["H", "sky"],
    ["F", "yellow"],
    ["X", "gray"],
  ]);

  let results: Results = { queryResults: [] };
  let queryIdx = 0;
  let width = 0;
  let alignmentProgress = "";
  let alignment = false;
  let cellWidth = 13;
  let cellHeight = 15;
  $: items = queryIdx < results.queryResults.length ? results.queryResults[queryIdx].items : [];
  $: width = items.length > 0 ? items[0].sequence.length * cellWidth : 0;
  $: canvasWidth = items.length > 0 ? Math.max(...items.map(i => i.sequence.length)) * cellWidth : 0;
  $: canvasHeight = items.length > 0 ? items.length * cellHeight : 0;;
  let clientHeight = 0;
  let clientWidth = 0;
  let states = [];

  

  function addToStates() {
    if (queryIdx >= results.queryResults.length) return;
    states.push(results.queryResults[queryIdx].items)
  }

  function resetStates() {
    states = []
    addToStates()
  }

  async function getResults() {
    results = await Api.getResults(id);
    resetStates();
    console.log(results.queryResults[0].items[178].name, results.queryResults[0].items[178].sequence)
    
  }

  getResults();

  let rowsNamesElement: HTMLTableElement;
  let rowsElement: HTMLTableElement;
  let highlightElement: HTMLTableElement;
  let canvas:HTMLCanvasElement;
  let ctx: CanvasRenderingContext2D;

  $: ctx =  (canvas ? canvas.getContext('2d', {}) : undefined);

  let namesMinWidth = 300;
  let namesSelected = [];
  let buffer = 15;
  let scrollTop = 0;
  let scrollLeft = 0;
  $: visibleVerticalItemCount = Math.round(clientHeight / 15) + 2 * buffer; 
  $: visibleHorizontalItemCount = Math.round(clientWidth / 13) + 2 * buffer; 
  let visibleVerticalBegin = 0;
  let visibleHorizontalBegin = 0;
  $: visibleCells = items.slice(visibleVerticalBegin, visibleVerticalBegin + visibleVerticalItemCount)
                     .map((item) => item.sequence.slice(visibleHorizontalBegin, visibleHorizontalBegin + visibleHorizontalItemCount));
  function handleScroll(e: UIEvent & { currentTarget: HTMLTableElement }) {
    rowsNamesElement.scrollTop = e.currentTarget.scrollTop;
    scrollTop = e.currentTarget.scrollTop;
    scrollLeft = e.currentTarget.scrollLeft;
    visibleVerticalBegin = Math.max(0, Math.floor(scrollTop / 15) - buffer);
    visibleHorizontalBegin = Math.max(0, Math.floor(scrollLeft / 13) - buffer);

  }

  onMount(() => {
    let frame;

    if (canvas) {
      ctx = canvas.getContext('2d', {});
      function draw() {
        if (ctx) {
          for (let i = 0; i < visibleCells.length; ++i) {
            for (let j = 0; j < visibleCells[i].length; ++j) {
              ctx.fillStyle = color_map.get(background_color.get(visibleCells[i][j]) || "white");
              let x = visibleHorizontalBegin * cellWidth + j * cellWidth
              let y = visibleVerticalBegin * cellHeight +  i * cellHeight
              ctx.fillRect(x, y, cellWidth, cellHeight);
              ctx.font = "11px Arial";
              ctx.fillStyle = "#000000";
              ctx.fillText(visibleCells[i][j], x + 2, y + cellHeight - 3);
            }
          }
        }
        
        frame = requestAnimationFrame(draw);
      }

      draw()
    }

    return () => cancelAnimationFrame(frame);
	});

  function draw() {
    if (ctx) {
      for (let i = 0; i < visibleCells.length; ++i) {
        for (let j = 0; j < visibleCells[i].length; ++j) {
          ctx.fillStyle = color_map.get(background_color.get(visibleCells[i][j]) || "white");
          let x = visibleHorizontalBegin * cellWidth + j * cellWidth
          let y = visibleVerticalBegin * cellHeight +  i * cellHeight
          ctx.fillRect(x, y, cellWidth, cellHeight);
          ctx.font = "11px Arial";
          ctx.fillStyle = "#000000";
          ctx.fillText(visibleCells[i][j], x + 2, y + cellHeight - 3);
        }
      }
    }
    
    return requestAnimationFrame(draw);
  }

  
  function handleTopScroll(e: UIEvent & { currentTarget: HTMLTableElement }) {
    rowsNamesElement.scrollTop = e.currentTarget.scrollTop;
    highlightElement.scrollTop = e.currentTarget.scrollTop;
  }

  function handleLeftScroll(e: UIEvent & { currentTarget: HTMLTableElement }) {
    rowsElement.scrollLeft = e.currentTarget.scrollLeft;
  }

  let namesHovering = -1;
  let namesEdited = -1;

  function splitterDragEnd(e: DragEvent) {
    namesMinWidth = e.clientX;
  }

  function namesOnClick(event: MouseEvent, i: number) {
    if (event.shiftKey && namesSelected.length > 0) {
      let first = namesSelected[0];
      namesSelected = [first];
      if (first > i) {
        [first, i] = [i, first];
      }
      for (let j = first; j <= i; ++j) {
        namesSelected.push(j);
      }
    } else if (!event.shiftKey || (event.shiftKey && namesSelected.length == 0)) {
      let idx = namesSelected.indexOf(i);
      if (idx == -1) {
        namesSelected = [i];
      } else {
        namesSelected = [];
      }
    }
  }

  function namesDragStart(event: DragEvent, i: number) {
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.dropEffect = "move";
    event.dataTransfer.setData("names", i.toString());
  }

  function namesDragOver(event: DragEvent) {
    if ([...event.dataTransfer.types].includes("names")) {
      event.preventDefault();
    }
  }

  function namesDragDrop(event: DragEvent, target: number) {
    event.dataTransfer.dropEffect = "move";
    const start = parseInt(event.dataTransfer.getData("names"));
    const newItems = Object.assign([], items);

    if (start < target) {
      newItems.splice(target + 1, 0, newItems[start]);
      newItems.splice(start, 1);
    } else {
      newItems.splice(target, 0, newItems[start]);
      newItems.splice(start + 1, 1);
    }

    items = newItems;
    results.queryResults[queryIdx].items = items
    namesHovering = null;
    addToStates();
  }

  function deleteSelected() {
    let newItems = [];
    for (let i = 0; i < items.length; ++i) {
      if (namesSelected.includes(i)) continue;
      newItems.push(items[i]);
    }
    items = newItems;
    results.queryResults[queryIdx].items = items
    namesSelected = [];
    addToStates();
  }

  function handleSave() {
    if (queryIdx >= results.queryResults.length) return;
    const a = document.createElement("a");
    const file = new Blob([items.map((i) => `>${i.name}\n${i.sequence}`).join("\n")], { type: "text/plain" });

    a.href = URL.createObjectURL(file);
    a.download = `${results.queryResults[queryIdx].query}.fasta`;
    a.click();

    URL.revokeObjectURL(a.href);
  }

  async function handleAlign() {
    if (queryIdx >= results.queryResults.length) return;
    alignment = true
    
    Api.alignSocket(
      results.queryResults[queryIdx], 
      (progress: string) => {alignmentProgress = progress},
      (result: ResultsQuery) => {
        let newResults = results
        results.queryResults[queryIdx] = result;
        results = newResults;
        alignment = false;
        
        resetStates();
      }
    );
  }

  async function handleDownloadAll() {
    if (queryIdx >= results.queryResults.length) return;
    const a = document.createElement("a");

    a.href = Api.resultsArchiveUrl(id);
    a.click();

    URL.revokeObjectURL(a.href);
  }

  function clearSelection()
  {
    if (window.getSelection) {window.getSelection().removeAllRanges();}
  }

  document.onkeydown = function (event) {
    // if (event.defaultPrevented) {
    //   return;
    // }
    if (event.key === "Escape") {
        namesSelected = [];
    } else if (event.key === "Delete") {
      deleteSelected();
    }
    else if (event.key === "z" && event.ctrlKey && states.length > 1 ) {
      states.pop();
      items = states[states.length - 1]
      results.queryResults[queryIdx].items = items
    }

    // event.preventDefault();
  };

  let isOpen = false;
</script>

<div class="alignment-page">
  <div class="alignment-header">
    <div class="header-splitter" />
    <div class="dropdown">
      <div class="dropbtn">{results.queryResults.length > 0 ? results.queryResults[queryIdx].query : "Queries"}</div>
      <div class="dropdown-content">
        {#each results.queryResults as queryResults, i (i)}
          <div on:click={() => {queryIdx = i;}}>{queryResults.query}</div>
        {/each}
      </div>
    </div>
    <div class="header-splitter" />
    <button class="alignment-button button-with-icon button-save tooltip" on:click={handleSave}> 
      <span class="tooltiptext">Save Alignment</span>
    </button>
    <div class="header-splitter" />
    <button class="alignment-button button-with-icon button-align tooltip" on:click={handleAlign}>
      <span class="tooltiptext">Muscle Alignment</span>
    </button>
    <div class="header-splitter" />
    <button class="alignment-button button-with-icon button-download tooltip" on:click={handleDownloadAll}>
      <span class="tooltiptext">Download Results</span>
    </button>
    <div class="header-splitter" />
    <div class="header-right-container"> 
      <button class="alignment-button button-with-icon button-contacts" on:click={() => navigate("/contacts/")}/>
      <div class="header-splitter" />
      <button class="alignment-button button-with-icon button-help" on:click={() => navigate("/help")}/>
      <div class="header-splitter" />
      <button class="alignment-button button-with-icon button-home" on:click={() => navigate("/")}/>
    </div> 
  </div>
  {#if alignment} 
    <div class="alignment-content-loading">
      <h2>Alignment Progress {alignmentProgress}</h2>
    </div>
  {:else}
    <div class="alignment-content">
       <table
        bind:this={rowsNamesElement}
        cellSpacing="0"
        cellPadding="0"
        style="min-width:{namesMinWidth}px; height:{clientHeight}px"
        class="table-rows-names"
      >
        {#each items as item, i (i)}
          <tr style="display:block; width:100%; line-height: 14px;">
            <td
              draggable={true}
              contenteditable={false}
              style="display:block; width:100%; font-family:arial; font-size:11px; justify-content: start; align-items: center; border-top: 1px solid LightGray;white-space: nowrap;"
              on:dragstart={(event) => namesDragStart(event, i)}
              on:drop|preventDefault={(event) => namesDragDrop(event, i)}
              on:dragover={namesDragOver}
              on:dragend={() => (namesHovering = -1)}
              on:dragenter={() => (namesHovering = i)}
              on:click={(e) => namesOnClick(e, i)}
              on:dblclick={(e) => { e.currentTarget.contentEditable="true"; namesEdited=i; e.currentTarget.focus()}} 
              on:blur={(e) => {e.currentTarget.contentEditable='false'; namesEdited=-1; clearSelection()}}
              class:is-active={namesHovering === i && namesEdited !== i}
              class:is-selected={namesSelected.includes(i) && namesEdited !== i}
            >
              {i + 1}. {item.name}
            </td>
          </tr>
        {/each}
      </table> 
      <div class="table-splitter" draggable={true} on:dragend={splitterDragEnd} />
      <div class="table-data"  bind:clientHeight={clientHeight} bind:clientWidth={clientWidth} on:scroll={handleScroll}>
        <canvas class="canvas" bind:this={canvas} width={canvasWidth} height={canvasHeight} />
      </div>
    </div>
    <!-- <div class="table-scroll" on:scroll={handleLeftScroll}>
      <div class="table-scroll-content" style="width:{width}px; height:1px" />
    </div> -->
  {/if}
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
    flex-flow: row;
    flex: 0 1 3%;
    background: #59253a;
    width: 100%;
    z-index: 10;
    /* height: 5%; */
  }

  .header-right-container {
    display: flex;
    flex-flow: row-reverse;
    flex: 1 1 5%;
    width: 100%;
    height: 100%;
  }

  .alignment-button {
    padding: 10px;
    text-align: center;
    text-decoration: none;
    display: block;
    font-size: 16px;
    cursor: pointer;
    outline: none;
    color: white;

    transition-duration: 0.4s;

    background-color: #59253a;
    border: none;
  }

  .tooltip .tooltiptext {
    visibility: hidden;
    width: 300px;
    background-color: #59253a;
    color: #b7a7b1;
    text-align: center;
    border: 2px solid #b7a7b1;

    position: absolute;
    left: 50%;
    top: 80%;
    z-index: 10;
    transition: opacity 0.3s;
  }

  .tooltip:hover .tooltiptext {
    visibility: visible;
    z-index: 10;
  }

  .alignment-button:hover {
    transform: translateY(2px);
  }

  .button-with-icon {
    background-repeat: no-repeat;
    background-size: contain;
    padding: 20px;
  }

  .button-align {
    background-image: url("/static/icons/icon_align.png");
  }

  .button-save {
    background-image: url("/static/icons/icon_save.png");
  }

  .button-download {
    background-image: url("/static/icons/icon_download_results.png");
  }

  .button-home {
    background-image: url("/static/icons/icon_home.png");
  }

  .button-help {
    background-image: url("/static/icons/icon_help.png");
  }

  .button-contacts {
    background-image: url("/static/icons/icon_contact.png");
  }

  .header-splitter {
    display: block;
    height: 100%;
    width: 1.1px;
    background-color: #59253a;
  }

  .dropbtn {
    font-family: Arial;
    background-color: #59253a;
    color: #b7a7b1;
    /* padding: 10px; */
    border: none;
    padding: 0px;
    /* font-size: 14px; */
    height: 100%;
    border: none;
    cursor: pointer;
    display: flex;
    justify-content: center;
    align-items: center;
    transition-duration: 0.4s;
  }

  .dropdown {
    font-family: Arial;
    position: relative;
    /* display: inline-block; */
    display: block;
    border: none;
    height: 100%;
    width: 300px;
  }

  .dropdown-content {
    font-family: Arial;
    display: none;
    position: absolute;
    background-color: #f9f9f9;
    min-width: 300px;
    box-shadow: 0px 8px 16px 0px rgba(0, 0, 0, 0.2);
    /* z-index: 1; */
  }

  .dropdown-content div {
    color: black;
    padding: 12px 16px;
    text-decoration: none;
    display: block;
  }

  .dropdown-content div:hover {
    background-color: #f1f1f1;
  }

  .dropdown:hover .dropdown-content {
    display: block;
  }

  .dropdown:hover .dropbtn {
    background-color: #378cc0;
  }

  .alignment-content {
    display: flex;
    flex: 1 1 auto;
    width: 100%;
    overflow: hidden;
    
    flex-flow: row;
    z-index: 1;
  }

  .alignment-content-loading {
    flex: 1 1 auto;
    width: 100%;
    height: 95%;
    font-family: Arial;
    display: flex;
    justify-content: center;
    align-items: center;
  }

  .table-rows-names {
    flex: 0 1 10%;
    width: 100%;
    height: 100%;
    display: block;
    overflow-y: hidden;
    overflow-x: hidden;
    table-layout: fixed;
  }

  .is-active {
    background-color: #3273dc;
    color: #fff;
  }

  .table-splitter {
    flex: 0 1 auto;
    min-width: 2px;
    display: block;

    background-color: LightGray;
    cursor: w-resize;

    position: relative;
  }

  .table-splitter:after {
    content: "";
    position: absolute;
    top: -1px;
    bottom: -1px;
    left: -5px;
    right: -5px;
  }

  .table-data {
    position: relative;
    flex: 1 1 auto;
    display: block;

    /* overflow-x: hidden; */
    /* overflow-y: hidden; */
    overflow-x: scroll;
    overflow-y: scroll;
    border-spacing: 0;

  }

  .canvas {
    /* flex: 1 1 auto; */
    /* display: block; */

    /* width: 100%; */
    /* height: 100%; */

    /* table-layout: fixed; */
    /* overflow-x: scroll; */
    /* overflow-y: scroll; */
    /* border-spacing: 0; */
    background: #eee; 
  }

  .table-highlight {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: -1;
    /* background: red; */
  }

  .table-highlight-table {
    width: 100%;
    height: 100%;
    display: block;
    overflow-y: hidden;
    overflow-x: hidden;
    table-layout: fixed;
  }

  .table-highlight-row {
    display: block;
    width: 100%;
    line-height: 15px;
  }

  .table-highlight-cell {
    display: block;
    width: 100%;
    height: 100%;
  }

  .is-selected {
    opacity: 0.5;
    background: #dca632;
    color: #fff;
  }

  /* .table-scroll {
    flex: 0 0 16px;
    width: 100%;
    height: 100%;
    overflow-x: scroll;
  } */
</style>
