<script>
  import { Router, Route, Link } from "svelte-routing";
  import SearchPage from "./SearchPage.svelte";
  import WaitingPage from "./WaitingPage.svelte";
  import AlignmentPage from "./AlignmentPage.svelte";
  import HelpPage from "./HelpPage.svelte";
  import ContactPage from "./ContactPage.svelte";

  export let url = "";
</script>

<Router url="{url}">
  <div class="app">
    <Route path="alignment/:id" let:params> <AlignmentPage id={params.id}/> </Route>
    <Route path="waiting/:id" let:params> <WaitingPage id={params.id}/> </Route>
    <Route path="help/" let:params> <HelpPage/> </Route>
    <Route path="contacts/" let:params> <ContactPage/> </Route>
    <Route path="/"><SearchPage /></Route>
  </div>
</Router>

<style>
  /* @import "https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css"; */
  
  .app {
    height: 100%;
    width: 100%;
  }
</style>