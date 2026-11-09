const formulario = document.getElementById("form-login");
const inputSenha = document.getElementById("isenha");
const inputConfirma = document.getElementById("iconfirmasenha");
const textoMsg = document.getElementById("mensagem-erro");
const botao = document.getElementById("join");

const token = new URLSearchParams(window.location.search).get("token");

if (!token) {
    textoMsg.textContent = "Link inválido.";
    botao.disabled = true;
}

formulario.addEventListener("submit", async function (evento) {
    evento.preventDefault();
    textoMsg.style.color = "red";
    textoMsg.textContent = "";

    const senha = inputSenha.value;
    const confirmaSenha = inputConfirma.value;

    if (senha !== confirmaSenha) {
        textoMsg.textContent = "As senhas não coincidem";
        return;
    }

    botao.disabled = true;

    try {
        const resposta = await fetch("http://127.0.0.1:5000/redefinir-senha", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ token: token, senha: senha })
        });
        const dados = await resposta.json();

        if (!resposta.ok) {
            textoMsg.textContent = dados.erro;
            botao.disabled = false;
            return;
        }

        textoMsg.style.color = "green";
        textoMsg.textContent = "Senha redefinida! Redirecionando para o login...";
        setTimeout(() => {
            window.location.href = "../index.html";
        }, 2000);
    } catch (erro) {
        textoMsg.textContent = "Não foi possível conectar ao servidor.";
        botao.disabled = false;
    }
});