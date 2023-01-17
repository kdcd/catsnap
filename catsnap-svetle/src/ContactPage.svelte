<script lang="ts">
    import { navigate } from "svelte-routing";

</script>

<style>
  .contact-page {
    display: flex;
    flex-flow: column;
    height: 100%;
    width: 100%;
  }

  .contact-header {
    font-family:Arial;
    display: flex;
    flex-flow: column;
    align-items: center;
    flex: 1 0 90px;
    background: #59253a;
    width: 100%;
    color: white;
  }

  .contact-header-text {
    /* padding:0px;
    margin:10px; */
    color: #b7a7b1;
    align-items: center;
    justify-content: center; 
  }
  
  .contact-content {
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

<div class="contact-page">
  <div class="contact-header"> 
    <h1 class="contact-header-text">Contacts</h1>
    <div style="position: absolute; top: 0; display: flex; flex-direction: row; justify-content: flex-end; align-items: center; width: 70%;" > 
      <button class="header-button" style = "background-image: url('/static/icons/icon_home.png');" on:click={() => navigate("/")}></button>
      <button class="header-button" style = "background-image: url('/static/icons/icon_help.png');" on:click={() => navigate("/help/")}></button>
    </div>
    
  </div>
  <div class="contact-content">

    Should you have any difficulties using Catsnap please send us an email to catsnap.help@gmail.com. This site has been created to make Catsnap available to a broader audience of experimental biologists and we will be happy to assist you in using it.


  </div>
</div>

