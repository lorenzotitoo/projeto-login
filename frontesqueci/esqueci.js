const formulario = document.getElementById("form-login");
const inputEmail = document.getElementById("iemail");
const textoMsg = document.getElementById("mensagem-erro");
const botao = document.getElementById("join");

formulario.addEventListener("submit", async function (evento) {
    evento.preventDefault();
    botao.disabled = true;
    textoMsg.style.color = "red";
    textoMsg.textContent = "";

    try {
        const resposta = await fetch(`${API_URL}/esqueci-senha`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: inputEmail.value })
        });
        const dados = await resposta.json();

        textoMsg.style.color = resposta.ok ? "green" : "red";
        textoMsg.textContent = resposta.ok ? dados.mensagem : dados.erro;
    } catch (erro) {
        textoMsg.textContent = "Não foi possível conectar ao servidor.";
    } finally {
        botao.disabled = false;
    }
});