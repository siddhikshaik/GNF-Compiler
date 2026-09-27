const $=s=>document.querySelector(s);
const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const sleep=ms=>new Promise(r=>setTimeout(r,ms));

function renderStats(d){
  const data=[["Variables",d.variables.length],["Terminals",d.terminals.length],["Productions",d.production_count],["GNF issues",d.gnf_violations]];
  $("#stats").innerHTML=data.map(([k,v])=>`<div class="stat">${k}<b>${v}</b></div>`).join("");
}
function renderDiagnostics(d){
  let html=`<strong>Start:</strong> ${esc(d.start)}<br>
  <strong>Variables:</strong> ${esc(d.variables.join(", ")||"—")}<br>
  <strong>Terminals:</strong> ${esc(d.terminals.join(", ")||"—")}<br>
  ε-productions: ${d.epsilon_count} · Unit productions: ${d.unit_count} · Direct left recursion: ${d.left_recursion_count}`;
  if(d.violations?.length){
    html+=`<div style="margin-top:12px"><strong>GNF issues</strong></div>`;
    html+=d.violations.map(v=>`<div class="issue"><b>${esc(v.lhs)} → ${esc(v.rhs)}</b><br>${esc(v.reason)}</div>`).join("");
    $("#diagnosticBadge").textContent="ISSUES";
    $("#diagnosticBadge").className="status bad";
  }else{
    html+=`<div style="margin-top:12px;color:#166534;font-weight:800">No GNF violations detected.</div>`;
    $("#diagnosticBadge").textContent="VALID";
    $("#diagnosticBadge").className="status ok";
  }
  $("#diagnostics").innerHTML=html;
}
function attachRipples(){
  document.querySelectorAll("button").forEach(btn=>{
    btn.addEventListener("click",e=>{
      const r=document.createElement("span");r.className="ripple";
      const rect=btn.getBoundingClientRect();const size=Math.max(rect.width,rect.height);
      r.style.width=r.style.height=size+"px";
      r.style.left=e.clientX-rect.left-size/2+"px";r.style.top=e.clientY-rect.top-size/2+"px";
      btn.appendChild(r);setTimeout(()=>r.remove(),600);
    });
  });
}
async function analyze(){
  const r=await fetch("/api/analyze",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({grammar:$("#grammar").value})});
  const d=await r.json(); if(!d.ok){showError(d.error);return}
  renderStats(d);renderDiagnostics(d);
}
function showError(msg){
  $("#pipeline").innerHTML=`<div class="issue"><b>Cannot process grammar</b><br>${esc(msg)}</div>`;
  $("#resultBadge").textContent="ERROR";$("#resultBadge").className="status bad";
}
async function convert(){
  $("#convert").disabled=true;$("#convert").textContent="Compiling…";
  $("#pipeline").innerHTML="";
  $("#progressBar").style.width="0%";
  $("#resultBadge").textContent="RUNNING";$("#resultBadge").className="status neutral";
  try{
    const r=await fetch("/api/convert",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({grammar:$("#grammar").value})});
    const d=await r.json();
    if(!r.ok||!d.ok){showError(d.error||"Conversion failed.");return}
    renderStats(d.result);renderDiagnostics(d.result);
    const stages=d.stages;
    for(let i=0;i<stages.length;i++){
      const s=stages[i];
      const wrapper=document.createElement("div");
      wrapper.className="stage";
      wrapper.innerHTML=`<div class="stage-number active">${String(i+1).padStart(2,"0")}</div>
      <div class="stage-card"><div class="stage-head"><b>${esc(s.name)}</b><span class="kind">${esc(s.kind)}</span></div>
      <div class="stage-body"><p class="stage-desc">${esc(s.description)}</p><pre class="grammar">${esc(s.grammar)}</pre></div></div>`;
      $("#pipeline").appendChild(wrapper);
      $("#progressBar").style.width=((i+1)/stages.length*100)+"%";
      wrapper.scrollIntoView({behavior:"smooth",block:"nearest"});
      await sleep(350);
      wrapper.querySelector(".stage-number").classList.remove("active");
    }
    const valid=d.complete_gnf;
    $("#resultBadge").textContent=valid?"GNF VALID":"GNF INVALID";
    $("#resultBadge").className="status "+(valid?"ok":"bad");
    const report=$("#finalReport");
    report.classList.remove("hidden");
    report.innerHTML=`<div class="panel-title"><div><span class="step">04</span><h3>Final Compiler Report</h3></div><span class="status ${valid?"ok":"bad"}">${valid?"VERIFIED":"CHECK REQUIRED"}</span></div>
      <div class="report-grid">
      <div class="report-item"><small>Variables</small><b>${d.result.variables.length}</b></div>
      <div class="report-item"><small>Terminals</small><b>${d.result.terminals.length}</b></div>
      <div class="report-item"><small>Productions</small><b>${d.result.production_count}</b></div>
      <div class="report-item"><small>GNF violations</small><b>${d.result.gnf_violations}</b></div></div>
      <div class="${valid?"report-ok":"report-bad"}">${valid?"✓ Every production satisfies the implemented GNF validator.":"⚠ The final grammar still contains a production that does not satisfy the GNF validator."}</div>`;
    report.scrollIntoView({behavior:"smooth",block:"start"});
  }catch(e){showError(e.message)}
  finally{$("#convert").disabled=false;$("#convert").innerHTML="Run GNF Compiler <span>→</span>";}
}
$("#analyze").onclick=analyze;$("#convert").onclick=convert;
attachRipples();analyze();

const glow=document.querySelector(".cursor-glow");
window.addEventListener("pointermove",e=>{glow.style.left=e.clientX+"px";glow.style.top=e.clientY+"px"});
