() => {
  // Read rendered DOM only. Never toggle mark, collect, answer or note controls.
  const text = e => e ? e.textContent.trim() : '';
  const cssPath = el => {
    const parts=[];
    while(el && el.nodeType===1 && el!==document.documentElement){
      const tag=el.tagName.toLowerCase();
      const siblings=Array.from(el.parentElement?.children||[]).filter(x=>x.tagName===el.tagName);
      parts.unshift(tag+':nth-of-type('+(siblings.indexOf(el)+1)+')');el=el.parentElement;
    }
    return 'html > '+parts.join(' > ');
  };
  const blocks = root => {
    const out=[];let pending='';
    const flush=()=>{if(pending.trim())out.push({type:'text',text:pending.trim()});pending='';};
    const walk=n=>{
      if(n.nodeType===3){pending+=n.textContent;return;}
      if(n.nodeType!==1)return;
      const tag=n.tagName.toLowerCase();
      if(['script','style','button','input','video','audio'].includes(tag)||n.matches('.title-right,.result-common-labels,.toggle-btn,[id^="section-video"],.solution-title-container svg'))return;
      if(tag==='textarea'){pending+=n.value||'';return;}
      if(tag==='img'){
        flush();out.push({type:'image',src:n.getAttribute('data-src')||n.currentSrc||n.getAttribute('src'),alt:n.getAttribute('alt')||'图片',capture_selector:cssPath(n)});return;
      }
      if(tag==='canvas'||tag==='svg'){
        if(n.closest('.title,.solution-title-container'))return;
        flush();out.push({type:'image',src:null,alt:'页面渲染图',capture_selector:cssPath(n),capture_kind:tag});return;
      }
      if(n.matches('.katex,.MathJax')){
        const tex=n.querySelector('annotation[encoding="application/x-tex"]');
        if(tex){pending+='$'+tex.textContent+'$';return;}
      }
      if(tag==='br'){pending+='\n';return;}
      if(tag==='table'){
        flush(); const rows=Array.from(n.querySelectorAll('tr')).map(r=>Array.from(r.children).map(c=>text(c).replace(/\|/g,'\\|')));
        if(rows.length){out.push({type:'text',text:rows.map((r,i)=>'| '+r.join(' | ')+' |'+(i===0?'\n| '+r.map(()=>'---').join(' | ')+' |':'')).join('\n')});}
        for(const img of n.querySelectorAll('img'))walk(img);return;
      }
      const separate=['p','div','article','section','li','h1','h2','h3','h4','h5','h6'].includes(tag);
      if(separate && !n.matches('.user-answer-content,.content-text'))flush();
      const wrap=({strong:'**',b:'**',em:'*',i:'*',u:'<u>',sup:'<sup>',sub:'<sub>'})[tag] || (/underline/.test(n.style.textDecoration)?'<u>':null);
      if(wrap)pending+=wrap;
      for(const child of n.childNodes)walk(child);
      if(wrap)pending+=wrap.startsWith('<')?wrap.replace('<','</'):wrap;
      if(separate && !n.matches('.user-answer-content,.content-text'))flush();
    };
    if(root)walk(root);flush();return out;
  };
  const cards=Array.from(document.querySelectorAll('.answer-btn'));
  const questions=Array.from(document.querySelectorAll('app-ti')).filter(e=>e.querySelector('.title-index')).map((root,index)=>{
    const number=parseInt(text(root.querySelector('.title-index')),10)||index+1;
    const button=cards.find(e=>parseInt(text(e),10)===number);
    const card=button?{marked:!!button.parentElement.querySelector('.mark'),collected:button.classList.contains('collected')||!!button.parentElement.querySelector('.collect')}:{};
    const toolbar={};
    for(const [attr,key] of [['标记','marked'],['收藏','collected']]){
      const tool=root.querySelector('[apptooltip="'+attr+'"]');
      if(tool)toolbar[key]=!!tool.querySelector('.active');
    }
    const selected=Array.from(root.querySelectorAll('.input-radio.correct,.input-radio.wrong,.input-checkbox.correct,.input-checkbox.wrong')).map(text);
    const answer=root.querySelector('.user-answer-pre,.result-answer-content');
    let user_answer=selected.length?selected.join(','):null;
    if(answer){
      const paras=answer.querySelectorAll('.paper-writing-paragraph');
      user_answer=paras.length?Array.from(paras).map(p=>Array.from(p.querySelectorAll('.content-text')).map(x=>x.textContent).join('')).join('\n'):text(answer);
    }
    const container=root.querySelector('.ti-container');
    const correctness=['correct','wrong','unanswered'].find(x=>container?.classList.contains(x))||null;
    const qid=root.getAttribute('data-question-key')||root.querySelector('[id^="section-solution-"]')?.id.replace('section-solution-','')||null;
    let content=blocks(root.querySelector('.ti-content')||root);
    // Materials are separate siblings of the question component on the current site.
    const materials=[];
    const left=root.closest('.resizable-container')?.querySelector(':scope > .left');
    if(left)materials.push(...blocks(left));
    let sibling=root.previousElementSibling;
    while(sibling && sibling.tagName!=='APP-TI'){
      if(/material/i.test(sibling.tagName+' '+sibling.className))materials.unshift(...blocks(sibling));
      sibling=sibling.previousElementSibling;
    }
    const sections=Array.from(root.querySelectorAll('section[id]')).filter(s=>!s.id.startsWith('section-video')).map(s=>({id:s.id,title:text(s.querySelector('.solution-title')),text:text(s)}));
    const grading=Array.from(root.querySelectorAll('.paper-writing-paragraph')).map(p=>Array.from(p.querySelectorAll('.user-answer-content')).map(s=>({text:text(s.querySelector('.content-text')),classes:s.className,text_classes:s.querySelector('.content-text')?.className||'',score:text(s.querySelector('.user-answer-content-score'))})));
    return {number,question_id:qid,card,toolbar,flag_evidence:{card_classes:button?.className||null,toolbar_available:Object.keys(toolbar)},user_answer,correct_answer:text(root.querySelector('.correct-answer'))||null,correctness,
      options:Array.from(root.querySelectorAll('.choice-radio,.choice-checkbox')).map(e=>({label:text(e.querySelector('.input-radio,.input-checkbox')),text:text(e),selected:!!e.querySelector('.correct,.wrong')})),
      sections,grading,blocks:[...materials,...content],answer_capture_selector:answer?cssPath(answer):null};
  });
  const body=document.body.innerText;
  const total=body.match(/共计\s*(\d+)\s*题/);
  const first=document.querySelector('app-ti');
  const firstText=first?.innerText;
  const boundary=firstText?body.indexOf(firstText):-1;
  const summary=boundary>=0?body.slice(0,boundary):body.slice(0,5000);
  return {title:document.title,summary,expected_count:total?Number(total[1]):(cards.length||null),questions,issues:[]};
}
