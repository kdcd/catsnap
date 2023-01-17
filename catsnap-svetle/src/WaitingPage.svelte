<script lang="ts">
  import {Api} from './Api';
  import { navigate } from "svelte-routing";
import type { ProgressResponse } from './Models';

  export let id;

  let status: ProgressResponse = {progress: 0, description: "Starting"};

	async function getProgress() {
    status = await Api.getProgress(id)
    if (status.progress < 100) { 
      setTimeout(getProgress, 1000);
    } else {
      setTimeout(() => navigate("/alignment/" + id), 500);
    }
	}

  getProgress()
</script>


<style>
  .waiting-page {
    display: flex;
    flex-flow: column;
    height: 100%;
    width: 100%;
  }

  .waiting-header {
    display: flex;
    flex-flow: column;
    align-items: center;
    flex: 0 1 5%;
    background: #59253a;
    width: 100%;
  }
  
  .waiting-content {
    display: flex;
    flex-flow: column;
    flex: 1 1 auto;
    width: 100%;
    justify-content: center;
    align-items: center;
  }

    
  @keyframes animate-stripes {
      0% {
          background-position: 0 0;
      }

      100% {
          background-position: 60px 0;
      }
  }

  .progress-bar {
      background-color: #59253a;
      height: 45px;
      width: 450px;
      margin: 50px auto;
      border-radius: 5px;
      box-shadow: 0 1px 5px #000 inset, 0 1px 0 #444;
  }

  .stripes {
      background-size: 30px 30px;
      background-image: linear-gradient(
          135deg,
          rgba(255, 255, 255, .15) 25%,
          transparent 25%,
          transparent 50%,
          rgba(255, 255, 255, .15) 50%,
          rgba(255, 255, 255, .15) 75%,
          transparent 75%,
          transparent
      );
  }

  .stripes.animated {
    animation: animate-stripes 0.6s linear infinite;
  }

  .stripes.animated.slower {
    animation-duration: 1.25s;
  }

  .stripes.reverse {
    animation-direction: reverse;
  }

  .progress-bar-inner {
    display: block;
    height: 45px;
    background-color: #3F88C5;
    border-radius: 3px;
    box-shadow: 0 1px 0 rgba(255, 255, 255, .5) inset;
    position: relative;
    animation: auto-progress 10s infinite linear;
  }

  .progress-description {
    font-family:Arial;
    display: flex;
    justify-content: center;
    align-items: center;
  }

</style>


<div class="waiting-page">
  <div class="waiting-header"/>
  <div class="waiting-content">
    <div class="progress-bar-container">
      <h2 class="progress-description ">
        {@html status.description}
      </h2>
      <div class="progress-bar stripes animated reverse slower">
        <span class="progress-bar-inner" style="width:{status.progress}%"></span>
      </div>
    </div>
  </div>
</div>

