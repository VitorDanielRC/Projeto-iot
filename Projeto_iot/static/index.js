async function chamarElevador(andar) {
  const status = document.getElementById("status");
  const cabine = document.getElementById("cabine");

  status.innerText = `Chamando elevador para o ${andar}º andar...`;

  try {
    const resposta = await fetch(`/api/elevador/chamar/${andar}/`);
    const dados = await resposta.json();

    if (dados.status === "ok") {
      cabine.className = `cabine andar-${andar}`;
      status.innerText = `Elevador enviado para o ${andar}º andar`;
    } else {
      status.innerText = "Erro ao chamar o elevador.";
    }
  } catch (error) {
    status.innerText = "Erro de conexão com a API.";
    console.error(error);
  }
  async function finalizarEntrega() {
  mostrarMensagem("Finalizando entrega e liberando o elevador...", false);

  try {
    const resposta = await fetch("/api/elevador/finalizar/", {
      method: "POST"
    });

    const dados = await resposta.json();

    if (dados.status === "ok") {
      document.getElementById("statusEntrega").innerText = "Finalizado";
      mostrarMensagem(dados.mensagem, false);
    } else {
      mostrarMensagem(dados.mensagem || "Erro ao finalizar entrega.", true);
    }
  } catch (error) {
    mostrarMensagem("Erro ao finalizar a entrega.", true);
    console.error(error);
  }
}
}