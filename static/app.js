const sections = [
  {title:"01 / Core sensors",hint:"Four monitoring groups",fields:[
    {key:"current_a",label:"Pump current",unit:"A",min:0,max:6,step:.05},
    {key:"flow_l_min",label:"Permeate flow",unit:"L/min",min:0,max:3.5,step:.01},
    {key:"pressure_bar",label:"Pressure",unit:"bar",min:0,max:12,step:.1},
    {key:"raw_tds_ppm",label:"Raw-water TDS",unit:"ppm",min:1,max:1200,step:1},
    {key:"output_tds_ppm",label:"Output-water TDS",unit:"ppm",min:0,max:800,step:1},
  ]},
  {title:"02 / Filter history",hint:"Usage since installation",fields:[
    {key:"cumulative_litres",label:"Water produced",unit:"L",min:0,max:20000,step:10},
    {key:"filter_age_days",label:"Filter age",unit:"days",min:0,max:600,step:1},
    {key:"runtime_hours",label:"Pump runtime",unit:"hours",min:0,max:1500,step:1},
  ]},
  {title:"03 / Recent trends",hint:"Change over the last week",fields:[
    {key:"flow_trend_pct_week",label:"Flow change",unit:"% / week",min:-30,max:30,step:.1},
    {key:"current_trend_pct_week",label:"Current change",unit:"% / week",min:-30,max:30,step:.1},
    {key:"pressure_trend_pct_week",label:"Pressure change",unit:"% / week",min:-30,max:30,step:.1},
  ]},
];
const presets = {
  Healthy:{current_a:1.5,flow_l_min:1.7,pressure_bar:6.6,raw_tds_ppm:520,output_tds_ppm:34,cumulative_litres:2200,filter_age_days:90,runtime_hours:170,flow_trend_pct_week:-.4,current_trend_pct_week:.2,pressure_trend_pct_week:.1},
  Fouling:{current_a:2.1,flow_l_min:.93,pressure_bar:8.4,raw_tds_ppm:520,output_tds_ppm:58,cumulative_litres:8500,filter_age_days:310,runtime_hours:610,flow_trend_pct_week:-7.1,current_trend_pct_week:3.2,pressure_trend_pct_week:2.8},
  "Membrane issue":{current_a:1.6,flow_l_min:1.5,pressure_bar:6.6,raw_tds_ppm:520,output_tds_ppm:160,cumulative_litres:9800,filter_age_days:355,runtime_hours:730,flow_trend_pct_week:-1.4,current_trend_pct_week:.5,pressure_trend_pct_week:.4},
  "No flow":{current_a:2,flow_l_min:0,pressure_bar:8.1,raw_tds_ppm:520,output_tds_ppm:75,cumulative_litres:8000,filter_age_days:280,runtime_hours:550,flow_trend_pct_week:-20,current_trend_pct_week:4,pressure_trend_pct_week:2},
};
const sensorGroups=[
  {label:"Pump current",keys:["current_a"]},
  {label:"Permeate flow",keys:["flow_l_min"]},
  {label:"Pressure",keys:["pressure_bar"]},
  {label:"Dual TDS",keys:["raw_tds_ppm","output_tds_ppm"]},
];
const liveFields=[
  ["current_a","Pump current","A"],["flow_l_min","Permeate flow","L/min"],
  ["pressure_bar","Pressure","bar"],["raw_tds_ppm","Raw TDS","ppm"],
  ["output_tds_ppm","Output TDS","ppm"],
];
let simTimer,liveTimer,randomCount=0,randomCorrect=0;

function showPage(hardware){
  document.getElementById("simPage").hidden=hardware;
  document.getElementById("hardwarePage").hidden=!hardware;
  for(const [id,active] of [["navSim",!hardware],["navHardware",hardware]]){
    document.getElementById(id).classList.toggle("selected",active);
    if(active) document.getElementById(id).setAttribute("aria-current","page");
    else document.getElementById(id).removeAttribute("aria-current");
  }
  if(hardware) refreshPorts();
}
function makeFields(){
  const root=document.getElementById("sensorFields");
  root.innerHTML=sections.map(section=>`<div class="field-section"><div class="field-heading"><h3>${section.title}</h3><span>${section.hint}</span></div><div class="field-grid">${section.fields.map(f=>`<div class="field"><div class="field-top"><label for="f-${f.key}">${f.label}</label><span class="unit">${f.unit}</span></div><div class="field-bottom"><input aria-label="${f.label} slider" data-key="${f.key}" data-kind="range" type="range" min="${f.min}" max="${f.max}" step="${f.step}"><input id="f-${f.key}" data-key="${f.key}" data-kind="number" type="number" min="${f.min}" max="${f.max}" step="${f.step}"></div></div>`).join("")}</div></div>`).join("");
  root.addEventListener("input",event=>{
    if(!event.target.matches("input[data-key]")) return;
    const key=event.target.dataset.key;
    const kind=event.target.dataset.kind === "range" ? "number" : "range";
    root.querySelector(`input[data-key="${key}"][data-kind="${kind}"]`).value=event.target.value;
    document.querySelectorAll(".preset").forEach(button=>button.classList.remove("active"));
    document.getElementById("randomResult").hidden=true;
    clearTimeout(simTimer);simTimer=setTimeout(runSimulation,130);
  });
}
function setValues(values){
  Object.entries(values).forEach(([key,value])=>document.querySelectorAll(`#sensorFields input[data-key="${key}"]`).forEach(input=>input.value=value));
}
function getValues(){
  const values={};document.querySelectorAll('#sensorFields input[data-kind="number"]').forEach(input=>values[input.dataset.key]=Number(input.value));return values;
}
async function api(url,method="GET",body){
  const response=await fetch(url,{method,headers:body?{"Content-Type":"application/json"}:{},body:body?JSON.stringify(body):undefined});
  const data=await response.json();
  if(!response.ok)throw Error(Array.isArray(data.detail)?data.detail.map(e=>`${e.loc.at(-1)}: ${e.msg}`).join("; "):data.detail||"Request failed");
  return data;
}
async function runSimulation(){
  const note=document.getElementById("resultNote");
  try{
    const result=await api("/api/predict","POST",getValues());
    document.querySelector(".result-panel").className=`result-panel ${result.status}`;
    document.getElementById("statusIcon").textContent={normal:"✓",warning:"!",critical:"×",off:"–"}[result.status];
    document.getElementById("statusTitle").textContent=result.status;
    document.getElementById("statusDescription").textContent={normal:"These readings look healthy in the simulation.",warning:"This pattern needs a closer look.",critical:"This pattern needs inspection.",off:"No prediction while the pump is off."}[result.status];
    document.getElementById("rejectionValue").textContent=`${result.salt_rejection_pct.toFixed(1)}%`;
    document.getElementById("confidenceText").textContent=result.status==="off"?"Not evaluated":`Top class ${Math.round(result.model_confidence*100)}%`;
    for(const label of ["normal","warning","critical"]){const pct=Math.round((result.probabilities[label]||0)*100);const cap=label[0].toUpperCase()+label.slice(1);document.getElementById(`bar${cap}`).style.width=`${pct}%`;document.getElementById(`prob${cap}`).textContent=`${pct}%`;}
    note.className=`note-box ${result.status==="critical"?"error":""}`;note.textContent=result.notes.join(" ");
    return result;
  }catch(error){document.getElementById("statusTitle").textContent="Check inputs";note.className="note-box error";note.textContent=error.message;}
}
async function randomSample(){
  try{
    const sample=await api("/api/random-sample");
    setValues(sample.values);document.querySelectorAll(".preset").forEach(button=>button.classList.remove("active"));
    await runSimulation();randomCount++;if(sample.correct)randomCorrect++;
    const box=document.getElementById("randomResult");box.hidden=false;
    box.textContent=`Known simulated label: ${sample.expected_label.toUpperCase()} · Model: ${sample.predicted_label.toUpperCase()} · ${sample.correct?"Correct":"Missed"} · This session: ${randomCorrect}/${randomCount} correct`;
  }catch(error){const box=document.getElementById("randomResult");box.hidden=false;box.textContent=error.message;}
}
function renderSensorStatus(state){
  document.getElementById("sensorChecks").innerHTML=sensorGroups.map(group=>{
    const okay=group.keys.every(key=>state.sensor_status?.[key]==="replying");
    return `<div class="sensor-check ${okay?"okay":""}"><span>${group.label}</span><strong>${okay?"Replying":"Waiting"}</strong></div>`;
  }).join("");
}
async function refreshPorts(){
  try{const data=await api("/api/hardware/ports");const select=document.getElementById("portSelect");const selected=select.value;select.innerHTML='<option value="">Choose a serial port</option>';data.ports.forEach(port=>{const option=document.createElement("option");option.value=port.device;option.textContent=`${port.device} — ${port.description}`;select.append(option)});select.value=selected;}
  catch(error){document.getElementById("connectionMessage").textContent=error.message;}
}
async function connectBoard(){
  const port=document.getElementById("portSelect").value;
  if(!port){document.getElementById("connectionMessage").textContent="Plug in the board and choose its serial port first.";return;}
  try{await api("/api/hardware/connect","POST",{port});document.getElementById("connectionMessage").textContent=`Connected to ${port}. Waiting for JSON readings…`;}
  catch(error){document.getElementById("connectionMessage").textContent=error.message;}
}
async function checkSensors(){
  try{const state=await api("/api/hardware/check","POST");renderSensorStatus(state);document.getElementById("connectionMessage").textContent=state.all_replying?"All four sensor groups are sending fresh values.":(state.error||"Waiting for a fresh reply from every sensor group.");}
  catch(error){document.getElementById("connectionMessage").textContent=error.message;}
}
async function refreshLive(){
  try{const state=await api("/api/hardware/status");
    document.getElementById("liveValues").innerHTML=liveFields.map(([key,label,unit])=>`<div class="live-value"><span>${label}</span><strong>${state.values[key]===undefined?"—":Number(state.values[key]).toFixed(2)}</strong><small>${unit}</small></div>`).join("");
    document.getElementById("sampleTime").textContent=state.fresh?`Fresh reading · ${state.sample_count} packets received`:(state.error||"Waiting for a recent board message…");
  }catch(error){document.getElementById("sampleTime").textContent=error.message;}
}
async function predictHardware(){
  const output=document.getElementById("hardwarePrediction");
  try{const result=await api("/api/hardware/predict","POST",{filter_age_days:Number(document.getElementById("hardwareAge").value)});output.textContent=`Prediction: ${result.prediction.status.toUpperCase()} · Salt rejection ${result.prediction.salt_rejection_pct}% · ${result.prediction.notes.join(" ")}`;}
  catch(error){output.textContent=error.message;}
}
async function init(){
  makeFields();setValues(presets.Healthy);
  for(const [name,values] of Object.entries(presets)){const button=document.createElement("button");button.type="button";button.className=`preset ${name==="Healthy"?"active":""}`;button.textContent=name;button.addEventListener("click",()=>{document.querySelectorAll(".preset").forEach(item=>item.classList.remove("active"));button.classList.add("active");setValues(values);document.getElementById("randomResult").hidden=true;runSimulation()});document.getElementById("presets").append(button);}
  document.getElementById("navSim").addEventListener("click",()=>showPage(false));
  document.getElementById("navHardware").addEventListener("click",()=>showPage(true));
  document.getElementById("randomButton").addEventListener("click",randomSample);
  document.getElementById("refreshPorts").addEventListener("click",refreshPorts);
  document.getElementById("connectButton").addEventListener("click",connectBoard);
  document.getElementById("checkButton").addEventListener("click",checkSensors);
  document.getElementById("liveButton").addEventListener("click",()=>{const panel=document.getElementById("livePanel");panel.hidden=!panel.hidden;document.getElementById("liveButton").textContent=panel.hidden?"Open live view":"Close live view";if(!panel.hidden){refreshLive();liveTimer=setInterval(refreshLive,1000)}else clearInterval(liveTimer)});
  document.getElementById("predictHardware").addEventListener("click",predictHardware);
  try{const info=await api("/api/model-info");document.getElementById("simAccuracy").textContent=`${(info.status_model.accuracy*100).toFixed(1)}%`;document.getElementById("simF1").textContent=info.status_model.macro_f1.toFixed(3);document.getElementById("criticalRecall").textContent=`${(info.status_model.report.critical.recall*100).toFixed(1)}%`;}catch(error){console.error(error)}
  renderSensorStatus({sensor_status:{}});runSimulation();
}
init();
