import main

for q in [
    "arabuluculuga basvurmadan is davasina bakilabilir mi",
    "iscinin haber vermeden isten ayrilmasi kidem tazminati alabilir mi",
    "kentsel donusumde pay sahibinin rizasi olmadan yikim olur mu",
]:
    docs = main.corpus_rank(q, 6)
    print("SORU:", q[:50])
    for d in docs:
        print("   ->", d.metadata["source"][:70])
    print()
