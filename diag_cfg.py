import time

import laya

agent = laya.load("convaiinnovations/laya", subfolder="multilingual")
print("cfg:", {k: agent.cfg[k] for k in ("max_len", "head_max_len")})

soru = "Yabanci hangi hallerde sinir disi edilir?"
adaylar = [
 ("6458-54", "Madde 54 - Sinir disi etme karari valilikce verilir; ulusal guvenlik, kamu duzeni ve kamu sagligi tehlikesi bulunanlar hakkinda uygulanir."),
 ("6458-53", "Madde 53 - Sinir disi etme kararinin tebligi, gerekceleri, itiraz yollari ve bildirim kurallari bu maddede duzenlenir."),
 ("6458-55", "Madde 55 - Geri itilme yasagi; uluslararasi koruma basvurulari sirasinda temel ilkeler."),
 ("6706-5",  "Madde 5 - Uluslararasi isbirligi ilkeleri; adli yardimlasma taleplerinin iletilmesi."),
]

def cal(instr_etiket, instr):
    state = {"hukuki_soru": soru}
    questions = {}
    for i, (did, metin) in enumerate(adaylar):
        state["madde_%d" % i] = did + "\n" + metin[:400]
        questions["m%d" % i] = {"type": "noul", "instructions": instr % i}
    t0 = time.time()
    r = agent.predict(state, questions)
    skorlar = {did: round(r["answers"]["m%d" % i]["noul"], 3) for i, (did, _) in enumerate(adaylar)}
    print("  [{}] skorlar={} | {:.0f} ms".format(instr.split(",")[0][:38], skorlar, (time.time() - t0) * 1000))

instr_a = ("madde_%d alanindaki kanun maddesi, hukuki_soru alanindaki soruya DOGRUDAN hukuki dayanak olusturuyor mu? "
           "Ayni konu alaninda olmasi yetmez; sorulan hakki, sureyi veya sarti bu madde duzenlemelidir.")
cal("orijinal instr", instr_a)
instr_b = ("madde_%d alanindaki metin, sorudaki hakkin kosullarini bizzat tanimliyor mu? "
           "Yalnizca proseduru, tebligi veya baska bir maddeye atif yapan metinler icin 0 yaz. "
           "Madde hukuki_soru'daki talebi dogrudan duzenliyorsa 1.")
cal("keskin instr", instr_b)
diag_ok = True
if diag_ok:
    pass
ELEOF
