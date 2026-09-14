const formulario = document.getElementById('form-cadastro');
const inputNome = document.getElementById('inome');
const inputEmail = document.getElementById('iemail');
const inputSenha = document.getElementById('isenha');
const inputConfirmaSenha = document.getElementById('iconfirmasenha');
const textoErro = document.getElementById('mensagem-erro'); 
const botaoCadastrar = document.getElementById('join');

formulario.addEventListener("submit", async function(evento) {
    evento.preventDefault();
    textoErro.textContent = "";
    textoErro.style.color = "red";

    const nome = inputNome.value;
    const email = inputEmail.value 
    const senha = inputSenha.value 
    const confirmaSenha = inputConfirmaSenha.value  

    if ( senha !== confirmaSenha) {
        textoErro.textContent = "As senhas não coincidem"
        return;
    }
    
    botaoCadastrar.disabled = true;

    try {
        const resposta = await fetch("http://127.0.0.1:5000/usuarios", {
            method: "POST",
            headers: {
                "content-type": "application/json"
            },
            body: JSON.stringify({ nome: nome, email: email, senha: senha })
        });

        const dadosResposta = await resposta.json();

        if(!resposta.ok) {
            textoErro.textContent = dadosResposta.erro;
            botaoCadastrar.disabled = false;
            return;
        }

        textoErro.style.color = "green"
        textoErro.textContent = "Cadastro realizado! Redirecionando para o login...";

        setTimeout(() => {
            window.location.href = "../index.html";
        }, 1500);
    } catch (erro) {
        textoErro.textContent = "Não foi possível conectar ao servidor.";
        console.error(erro);
        botaoCadastrar.disabled = false;
    }
});

function configurarToggleSenha(idInput, idBotaoOlho) {
    const input = document.getElementById(idInput);
    const botaoOlho = document.getElementById(idBotaoOlho);

    botaoOlho.addEventListener("click", function () {
        const estaOculta = input.type === "password";
        input.type = estaOculta ? "text" : "password";
        botaoOlho.textContent = estaOculta ? "visibility" : "visibility_off";
    });
}

configurarToggleSenha("isenha", "toggle-isenha");
configurarToggleSenha("iconfirmasenha", "toggle-iconfirmasenha");