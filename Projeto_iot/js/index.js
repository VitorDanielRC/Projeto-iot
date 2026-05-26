const elevador = document.getElementById("elevador");
const andarAtualTexto = document.getElementById("andarAtual");

const posicoes = {
    1: 10,
    2: 110,
    3: 210,
    4: 310,
    5: 410
};

let ocupado = false;

function abrirPorta() {
    elevador.classList.add("abrir");
}

function fecharPorta() {
    elevador.classList.remove("abrir");
}

function irParaAndar(andar) {

    if (ocupado) return;

    ocupado = true;

    fecharPorta();

    setTimeout(() => {

        elevador.style.bottom = posicoes[andar] + "px";

        andarAtualTexto.textContent = andar;

        setTimeout(() => {

            abrirPorta();

            setTimeout(() => {
                fecharPorta();
                ocupado = false;
            }, 2000);

        }, 2200);

    }, 500);
}