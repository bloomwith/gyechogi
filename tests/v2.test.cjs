const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const html=fs.readFileSync(path.join(__dirname,'../index.html'),'utf8');
const SOURCE=JSON.parse(html.match(/<script id="source-data" type="application\/json">([\s\S]*?)<\/script>/)[1]);
const ctx=vm.createContext({SOURCE});
vm.runInContext(html.match(/<script id="checker-logic">([\s\S]*?)<\/script>/)[1],ctx);
function check(text){ctx.input=text; return JSON.parse(vm.runInContext('JSON.stringify(review(input))',ctx));}
const cases=[
 ['조달 성공 어순','자금조달에 성공한 경우 보수를 지급한다.',['R1']],
 ['조달 완료 어순','자금조달을 완료한 경우 수수료를 지급한다.',['R1']],
 ['조달금액','보수는 조달금액의 2%이다.',['R1']],
 ['성공보수','성공보수를 지급한다.',['R4']],
 ['성과 보수','성과 보수를 지급한다.',['R4']],
 ['아님 제외','중개 또는 대리에 대한 대가가 아님을 확인한다.',[]],
 ['자료 보장 제외','의뢰인은 자료가 정확함을 보장한다.',[]],
 ['투자 보장','투자 유치를 확약한다.',['R3']],
 ['성사 별도 제외','월 자문료는 자금조달 성사 여부와 별도로 지급한다.',[]],
 ['부정 목록','다음 업무는 포함하지 않는다.\n1. 금융기관 알선\n2. 투자 중개',[]],
 ['목록 종료','다음 업무는 포함하지 않는다.\n1. 금융기관 알선\n별도 업무\n투자를 중개한다.',['R2']],
];
for(const [name,text,want] of cases)test(name,()=>assert.deepEqual(check(text).codes.filter(x=>x.startsWith('R')),want));
test('조 제목과 별첨은 빈칸이 아니며 실제 자리표시자는 유지',()=>{
 const r=check('제1조 [목적]\n[별첨] [별표] [붙임]\n[관할 법원] ○○ __ {{금액}}');
 assert.deepEqual(r.codes.filter(x=>x.startsWith('BLANK')),['BLANK×4']);
});
test('C2는 성사와 관계있는 문장에서만 통과',()=>{
 assert.ok(check('보수의 명칭과 관계없이 지급한다.').codes.includes('C2'));
 assert.ok(!check('조달 성사 여부와 별도로 지급한다.').codes.includes('C2'));
});
test('C6와 C9는 독립 점검',()=>{
 assert.ok(check('면책 및 책임의 한계').codes.includes('C6'));
 assert.ok(!check('최종 판단 책임은 의뢰인이 부담한다.').codes.includes('C6'));
 assert.ok(check('최종 판단 책임은 의뢰인이 부담한다.').codes.includes('C9'));
 assert.ok(!check('손해배상은 받은 보수 총액을 한도로 한다.').codes.includes('C9'));
});
test('부정 번호 목록은 C1 중개 금지로 인정',()=>assert.ok(!check('다음 업무는 포함하지 않는다.\n1. 알선\n2. 중개').codes.includes('C1')));
test('11건 고정 정답',()=>{
 const wants=[[],['R1','R4','C2'],['R2','C1'],['BLANK×4'],['R3'],['C5','C7'],[],['R1','R2','R4','BLANK×1','C6','C9'],['R1','R4','BLANK×3'],['R1','R2','R4','BLANK×20','C1','C2'],['R1','R4','BLANK×14','C6','C9']];
 assert.equal(SOURCE.drafts.length,11);
 SOURCE.drafts.forEach((d,i)=>assert.deepEqual(check(d.text).codes,wants[i],d.name));
});
