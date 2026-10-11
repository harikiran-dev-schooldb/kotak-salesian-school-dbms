const yearData={
  "2026-27":{students:"1,842",collected:"₹1.28 Cr",pending:"₹18.6 L",attendance:"92.8%"},
  "2025-26":{students:"1,791",collected:"₹1.19 Cr",pending:"₹16.2 L",attendance:"91.6%"},
  "2024-25":{students:"1,744",collected:"₹1.08 Cr",pending:"₹14.9 L",attendance:"90.9%"}
};
const yearIds={"2024-25":1,"2025-26":2,"2026-27":3};
const demoStudents=[
  ["ADM•••1042","Student 1042","Grade 10 · A","Main campus","Continuing","94%"],
  ["ADM•••0831","Student 0831","Grade 9 · B","High school","Continuing","91%"],
  ["ADM•••1527","Student 1527","Grade 7 · A","Primary wing","New","97%"],
  ["ADM•••0419","Student 0419","Grade 10 · C","Main campus","Continuing","88%"],
  ["ADM•••1218","Student 1218","Grade 7 · B","Primary wing","Continuing","71%"],
  ["ADM•••0732","Student 0732","Grade 8 · A","High school","TC applied","86%"]
];
const demoPipelines=[
  ["students","Student registry","Google Sheets → students","1,842 records","10 Oct · 6:31 PM"],
  ["fees","Fees master","Google Sheets → fees_table","1,842 records","10 Oct · 6:36 PM"],
  ["daywise","Day-wise collection","School portal → PostgreSQL","4,218 records","10 Oct · 6:42 PM"],
  ["concessions","Fee concessions","School portal → PostgreSQL","96 records","10 Oct · 6:44 PM"],
  ["transactions","Atom transactions","Atom portal → reconciliation","4,218 records","10 Oct · 6:48 PM"],
  ["attendance","Attendance","Source reports → PostgreSQL","212,904 records","10 Oct · 6:52 PM"]
];
const titles={overview:"Overview",students:"Students",fees:"Fees & collections",attendance:"Attendance",concessions:"Concessions",transactions:"Transactions",refresh:"Data refresh"};
const sameOriginApi=location.hostname.endsWith(".vercel.app")?location.origin:"";
const state={apiUrl:sessionStorage.getItem("kotakApiUrl")||sameOriginApi,apiKey:sessionStorage.getItem("kotakApiKey")||"",role:"",connected:false,currentView:"overview"};

const $=selector=>document.querySelector(selector);
const escapeHtml=value=>String(value??"").replace(/[&<>'"]/g,char=>({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[char]));
const formatMoney=value=>{
  const amount=Number(value||0);
  if(Math.abs(amount)>=10000000)return `₹${(amount/10000000).toFixed(2).replace(/\.00$/,"")} Cr`;
  if(Math.abs(amount)>=100000)return `₹${(amount/100000).toFixed(1).replace(/\.0$/,"")} L`;
  return new Intl.NumberFormat("en-IN",{style:"currency",currency:"INR",maximumFractionDigits:0}).format(amount);
};
const formatDate=value=>value?new Intl.DateTimeFormat("en-IN",{day:"numeric",month:"short",year:"numeric"}).format(new Date(value)):"—";
const yearId=()=>yearIds[$("#yearSelect").value]||3;
const setText=(selector,value)=>{const element=$(selector);if(element)element.textContent=value};

async function api(path,options={}){
  if(!state.apiUrl||!state.apiKey)throw new Error("Connect the data API first");
  const response=await fetch(`${state.apiUrl}${path}`,{
    ...options,
    headers:{"X-API-Key":state.apiKey,"Content-Type":"application/json",...(options.headers||{})}
  });
  let payload={};
  try{payload=await response.json()}catch{payload={detail:`Server returned ${response.status}`}}
  if(!response.ok)throw new Error(payload.detail||`Request failed (${response.status})`);
  return payload;
}

function setConnectionBanner(message="Live PostgreSQL data is connected securely."){
  $("#dataBanner").classList.toggle("live",state.connected);
  setText("#dataMode",state.connected?"Live data":"Dashboard preview");
  setText("#dataMessage",state.connected?message:"Uses non-sensitive demonstration totals. Connect the secure server API for live data.");
  $("#connectionButton").textContent=state.connected?"✓":"↗";
  $("#connectionButton").title=state.connected?`Connected as ${state.role}`:"Connect data API";
}

function showView(id){
  state.currentView=id;
  document.querySelectorAll(".view").forEach(view=>view.classList.toggle("active",view.id===id));
  document.querySelectorAll(".nav-item").forEach(item=>item.classList.toggle("active",item.dataset.view===id));
  setText("#pageTitle",titles[id]||"Dashboard");
  $("#sidebar").classList.remove("open");
  window.scrollTo({top:0,behavior:"smooth"});
  if(state.connected)loadViewData(id);
}

function renderDemoStudents(filter=""){
  const query=filter.toLowerCase();
  $("#studentRows").innerHTML=demoStudents.filter(row=>row.join(" ").toLowerCase().includes(query)).map(row=>`<tr>${row.map((cell,index)=>index===4?`<td><span class="status-pill ${cell==='TC applied'?'warning':'success'}">${escapeHtml(cell)}</span></td>`:`<td>${escapeHtml(cell)}</td>`).join("")}</tr>`).join("")||`<tr><td colspan="6">No matching students</td></tr>`;
}

async function loadOverview(){
  const data=await api(`/api/overview?academic_year_id=${yearId()}`);
  setText('[data-metric="students"]',new Intl.NumberFormat("en-IN").format(data.students));
  setText('[data-metric="collected"]',formatMoney(data.fees_collected));
  setText('[data-metric="pending"]',formatMoney(data.pending_fees));
  setText('[data-metric="attendance"]',data.attendance_available?`${data.attendance_percent}%`:"Not loaded");
  setConnectionBanner(`Live data · ${data.academic_year} · Identifiers masked`);
}

async function loadStudents(search=""){
  const data=await api(`/api/students?academic_year_id=${yearId()}&limit=100&search=${encodeURIComponent(search)}`);
  $("#studentRows").innerHTML=data.items.map(item=>`<tr><td>${escapeHtml(item.admission_no)}</td><td>${escapeHtml(item.student)}</td><td>${escapeHtml(item.grade||"—")}</td><td>${escapeHtml(item.branch_id??"—")}</td><td><span class="status-pill ${item.status==='TC applied'?'warning':'success'}">${escapeHtml(item.status)}</span></td><td>—</td></tr>`).join("")||`<tr><td colspan="6">No matching students</td></tr>`;
}

async function loadFees(){
  const data=await api(`/api/fees?academic_year_id=${yearId()}&limit=30`);
  const summary=data.summary;
  setText("#expectedStat",formatMoney(summary.expected_fees));
  setText("#collectedStat",formatMoney(summary.fees_collected));
  setText("#feeConcessionStat",formatMoney(summary.concessions));
  const rate=summary.expected_fees?summary.fees_collected/summary.expected_fees*100:0;
  setText("#collectionRateStat",`${rate.toFixed(1)}%`);
  $("#feeRows").innerHTML=data.recent_payments.map(item=>`<tr><td>${escapeHtml(item.receipt||"—")}</td><td>${escapeHtml(item.admission_no)}</td><td>${formatDate(item.payment_date)}</td><td>${escapeHtml(item.payment_mode||"—")}</td><td>${escapeHtml(item.account_name||"—")}</td><td>${formatMoney(item.amount)}</td></tr>`).join("")||`<tr><td colspan="6">No collection records found</td></tr>`;
}

async function loadAttendance(){
  const data=await api(`/api/attendance?academic_year_id=${yearId()}`);
  const latest=data.latest_attendance_percent;
  setText("#attendanceToday",data.available&&latest!==null?`${latest}%`:"Not loaded");
  setText("#attendanceDateLabel",data.latest_date?`Latest recorded · ${formatDate(data.latest_date)}`:"Latest recorded day");
  $(".attendance-donut").style.background=data.available&&latest!==null?`conic-gradient(var(--green) 0 ${latest}%,#e8edf2 ${latest}%)`:"#e8edf2";
  if(data.available){
    $("#gradeBars").innerHTML=data.by_grade.map(item=>`<div class="grade-row"><span>Grade ${escapeHtml(item.grade)}</span><div><i style="width:${Math.min(100,item.attendance_percent)}%"></i></div><strong>${item.attendance_percent}%</strong></div>`).join("")||"<p>No grade totals available.</p>";
    setText("#lowAttendanceCount",`${data.low_attendance.length} students`);
    $("#attendanceRows").innerHTML=data.low_attendance.map(item=>`<tr><td>${escapeHtml(item.admission_no)}</td><td>Grade ${escapeHtml(item.grade)}</td><td>${escapeHtml(item.present)}</td><td>${escapeHtml(item.absent)}</td><td><span class="status-pill danger">${escapeHtml(item.attendance_percent)}%</span></td><td><button class="text-button">Review</button></td></tr>`).join("")||`<tr><td colspan="6">No students below 75%.</td></tr>`;
  }
}

async function loadConcessions(){
  const data=await api(`/api/concessions?academic_year_id=${yearId()}&limit=50`);
  setText("#concessionTotalStat",formatMoney(data.total_amount));
  setText("#beneficiaryStat",new Intl.NumberFormat("en-IN").format(data.beneficiaries));
  setText("#concessionAverageStat",formatMoney(data.beneficiaries?data.total_amount/data.beneficiaries:0));
  $("#concessionRows").innerHTML=data.items.map(item=>`<tr><td>${formatDate(item.date)}</td><td>${escapeHtml(item.student_number)}</td><td>${formatMoney(item.discount_given)}</td><td>${escapeHtml(item.academic_year_id)}</td></tr>`).join("")||`<tr><td colspan="4">No concessions found</td></tr>`;
}

async function loadTransactions(){
  const data=await api("/api/transactions/unmatched?limit=100");
  setText("#unmatchedStat",new Intl.NumberFormat("en-IN").format(data.total));
  setText("#unmatchedAmountStat",formatMoney(data.amount));
  $("#transactionRows").innerHTML=data.items.map(item=>`<tr><td>${escapeHtml(item.transaction)}</td><td>${escapeHtml(item.admission_no)}</td><td>${formatDate(item.txn_date)}</td><td>${formatDate(item.settlement_date)}</td><td>${formatMoney(item.amount)}</td><td><span class="status-pill warning">Unmatched</span></td></tr>`).join("")||`<tr><td colspan="6">No unmatched transactions</td></tr>`;
}

function renderPipelines(items=demoPipelines.map(([pipeline,title,description,records,time])=>({pipeline,title,description,records,time,available:true}))){
  $("#pipelineGrid").innerHTML=items.map(item=>{
    const title=item.title||item.pipeline.replace(/^./,char=>char.toUpperCase());
    const description=item.description||item.table;
    const records=item.records||`${new Intl.NumberFormat("en-IN").format(item.record_count||0)} records`;
    const badge=item.available!==false?'<span class="status-pill success"><i></i>Ready</span>':'<span class="status-pill warning">Not loaded</span>';
    return `<article class="pipeline-card"><header><h3>${escapeHtml(title)}</h3>${badge}</header><p>${escapeHtml(description)}</p><footer><span>${escapeHtml(records)}<br>${escapeHtml(item.time||"Live database")}</span><button class="refresh-button" data-pipeline="${escapeHtml(item.pipeline)}">Request refresh</button></footer></article>`;
  }).join("");
  document.querySelectorAll(".refresh-button").forEach(button=>button.addEventListener("click",()=>requestRefresh(button.dataset.pipeline)));
}

async function loadPipelines(){
  const data=await api("/api/pipeline/status");
  renderPipelines(data.items);
}

async function loadViewData(view){
  try{
    if(view==="overview")await loadOverview();
    if(view==="students")await loadStudents($("#studentSearch").value);
    if(view==="fees")await loadFees();
    if(view==="attendance")await loadAttendance();
    if(view==="concessions")await loadConcessions();
    if(view==="transactions")await loadTransactions();
    if(view==="refresh")await loadPipelines();
  }catch(error){setConnectionBanner(`Live connection error: ${error.message}`)}
}

async function loadAll(){
  await loadOverview();
  await Promise.allSettled([loadStudents(),loadFees(),loadAttendance(),loadConcessions(),loadTransactions(),loadPipelines()]);
}

const modal=$("#modal");
function openModal(title="Refresh request prepared",message="The web interface is ready. Connect the private pipeline API before enabling production refreshes."){
  $("#modalTitle").textContent=title;
  $("#modalTitle").nextElementSibling.textContent=message;
  modal.classList.add("open");modal.setAttribute("aria-hidden","false");
}
function closeModal(){modal.classList.remove("open");modal.setAttribute("aria-hidden","true")}

async function requestRefresh(pipeline){
  if(!state.connected){openModal();return}
  try{
    const result=await api(`/api/refresh/${encodeURIComponent(pipeline)}`,{method:"POST"});
    openModal("Refresh started",`${pipeline} refresh is running. Audit reference: ${result.audit_id}.`);
    await loadPipelines();
  }catch(error){openModal("Refresh not started",error.message)}
}

const connectionModal=$("#connectionModal");
function openConnection(){
  $("#apiUrl").value=state.apiUrl;
  $("#apiKey").value=state.apiKey;
  $("#connectionStatus").textContent=state.connected?`Connected as ${state.role}.`:"";
  connectionModal.classList.add("open");connectionModal.setAttribute("aria-hidden","false");
}
function closeConnection(){connectionModal.classList.remove("open");connectionModal.setAttribute("aria-hidden","true")}

async function connectApi(){
  const url=$("#apiUrl").value.trim().replace(/\/$/,"");
  const key=$("#apiKey").value.trim();
  const status=$("#connectionStatus");
  status.className="form-status";status.textContent="Checking secure connection…";
  if(!/^https?:\/\//.test(url)||!key){status.classList.add("error");status.textContent="Enter a valid API address and key.";return}
  const previous={apiUrl:state.apiUrl,apiKey:state.apiKey};
  state.apiUrl=url;state.apiKey=key;
  try{
    const session=await api("/api/session");
    state.role=session.role;state.connected=true;
    sessionStorage.setItem("kotakApiUrl",url);sessionStorage.setItem("kotakApiKey",key);
    status.classList.add("success");status.textContent=`Connected as ${session.role}. Loading live data…`;
    await loadAll();closeConnection();
  }catch(error){
    state.apiUrl=previous.apiUrl;state.apiKey=previous.apiKey;state.connected=false;
    status.classList.add("error");status.textContent=error.message;
  }
}

function disconnectApi(){
  sessionStorage.removeItem("kotakApiUrl");sessionStorage.removeItem("kotakApiKey");
  state.apiUrl="";state.apiKey="";state.role="";state.connected=false;
  closeConnection();location.reload();
}

document.querySelectorAll("[data-view]").forEach(button=>button.addEventListener("click",()=>showView(button.dataset.view)));
document.querySelectorAll("[data-view-target]").forEach(button=>button.addEventListener("click",()=>showView(button.dataset.viewTarget)));
$("#menuButton").addEventListener("click",()=>$("#sidebar").classList.toggle("open"));
$("#yearSelect").addEventListener("change",event=>{
  if(state.connected){loadAll();return}
  const values=yearData[event.target.value];
  Object.entries(values).forEach(([key,value])=>setText(`[data-metric="${key}"]`,value));
});

let searchTimer;
$("#studentSearch").addEventListener("input",event=>{
  clearTimeout(searchTimer);
  if(state.connected)searchTimer=setTimeout(()=>loadStudents(event.target.value),250);
  else renderDemoStudents(event.target.value);
});

const grades=[96,94,93,92,95,90,89,91,94,88];
$("#gradeBars").innerHTML=grades.map((value,index)=>`<div class="grade-row"><span>Grade ${index+1}</span><div><i style="width:${value}%"></i></div><strong>${value}%</strong></div>`).join("");
renderDemoStudents();renderPipelines();setConnectionBanner();

$("#modalClose").addEventListener("click",closeModal);$("#modalDone").addEventListener("click",closeModal);
modal.addEventListener("click",event=>{if(event.target===modal)closeModal()});
$("#connectionButton").addEventListener("click",openConnection);$("#connectionClose").addEventListener("click",closeConnection);
$("#connectButton").addEventListener("click",connectApi);$("#disconnectButton").addEventListener("click",disconnectApi);
connectionModal.addEventListener("click",event=>{if(event.target===connectionModal)closeConnection()});
document.addEventListener("keydown",event=>{if(event.key==="Escape"){closeModal();closeConnection()}});

if(state.apiUrl&&state.apiKey){
  api("/api/session").then(session=>{state.role=session.role;state.connected=true;return loadAll()}).catch(()=>{state.connected=false;setConnectionBanner("Saved connection could not be verified. Open connection settings to retry.")});
}
