(async function(){
  const section=document.getElementById("announcements");
  const feed=document.getElementById("announcementFeed");
  const client=window.MOAMOA_CLOUD&&window.MOAMOA_CLOUD.client;
  if(!section||!feed||!client)return;
  try{
    const {data,error}=await client.from("announcements")
      .select("title,body,published_at,created_at")
      .eq("is_published",true)
      .order("published_at",{ascending:false})
      .limit(5);
    if(error)throw error;
    if(!data||!data.length)return;
    data.forEach(item=>{
      const card=document.createElement("article");
      card.className="announcement-card";
      const heading=document.createElement("h3");
      heading.textContent=item.title||"공지사항";
      const date=document.createElement("time");
      const stamp=item.published_at||item.created_at;
      date.textContent=stamp?new Date(stamp).toLocaleDateString("ko-KR"):"";
      const body=document.createElement("p");
      body.textContent=item.body||"";
      card.append(heading,date,body);
      feed.append(card);
    });
    section.hidden=false;
  }catch(error){
    console.error("MOAMOA announcements load failed:",error);
  }
})();
