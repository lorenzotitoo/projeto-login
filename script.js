const formulario = document.getElementById("form-login");
const inputEmail = document.getElementById("iemail")
const inputSenha = document.getElementById("isenha")
const textoErro = document.getElementById("mensagem-erro")

const botaoEntrar = document.getElementById("join");


formulario.addEventListener('submit', async function(evento) {
    evento.preventDefault();
    botaoEntrar.disabled = true;
    textoErro.textContent = "";
    const email = inputEmail.value;
    const senha = inputSenha.value;

    try {
        const resposta = await fetch("http://127.0.0.1:5000/login", {
            method: "POST",
            headers: {
                "content-type": "application/json"
            },
            body: JSON.stringify({email: email, senha: senha})    
        });

        const dadosResposta = await resposta.json();

        if (!resposta.ok) {
            textoErro.style.color = "red";
            textoErro.textContent = dadosResposta.erro;
            botaoEntrar.disabled = false;
            return;

        }

        localStorage.setItem("token", dadosResposta.token);
        localStorage.setItem("usuarioLogado", JSON.stringify(dadosResposta.usuario))
        setTimeout(() => {
                window.location.href = "/frontpainel/painel.html"; 
                botaoEntrar.disabled = false;
            }, 1000);
    } catch (erro) {
        textoErro.textContent = "Não foi possível conectar ao servidor.";
        console.error(erro);
        botaoEntrar.disabled = false;
    } 

});