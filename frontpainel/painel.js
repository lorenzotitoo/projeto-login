const tokenAcesso = localStorage.getItem("token");

if (!tokenAcesso) {
    window.location.href = "../frontlogin/index.html";
}

function fazerLogout() {
    localStorage.removeItem("token");
    localStorage.removeItem("usuarioLogado");
    window.location.href = "../frontlogin/index.html";
}

document.getElementById("sair").addEventListener("click", function () {
    fazerLogout();
});



async function carregarPerfil() {
    try {
        const resposta = await fetch("http://127.0.0.1:5000/perfil", {
            method: "GET",
            headers: {
                "Authorization": `Bearer ${tokenAcesso}`
            }
        });

        if (!resposta.ok) {
            fazerLogout()
            return;
        }

        const usuario = await resposta.json()
        document.getElementById("nome-usuario").textContent = usuario.nome;
        document.getElementById("email-usuario").textContent = usuario.email;
    } catch (erro) {
        console.error(erro);
        window.location.href = "../frontlogin/index.html";
    }
}

carregarPerfil();


const formEditar = document.getElementById("form-editar")
const btnAtualizar = document.getElementById("btn-editar")
const msgEditar = document.getElementById("msg-editar")

formEditar.addEventListener('submit', async function(evento){
    evento.preventDefault();
    msgEditar.textContent = "";
    msgEditar.style.color = "red";

    const usuarioLogado = JSON.parse(localStorage.getItem('usuarioLogado'));
    const idUsuario = usuarioLogado.id;

    const novoNome = document.getElementById("novo-nome").value
    const novaSenha = document.getElementById("nova-senha").value
    const confirmaSenha = document.getElementById("confirma-senha").value

    if (novaSenha != confirmaSenha) {
        msgEditar.textContent = "A senha não coincide"
        return;
    }

    if (!novoNome && !novaSenha) {
        msgEditar.textContent = "Preencha pelo menos um campo para atualizar";
        return;
    }
    
    const dadosAtualizacao = {}
    if (novoNome) dadosAtualizacao.nome = novoNome;
    if (novaSenha) dadosAtualizacao.senha = novaSenha
    
    btnAtualizar.disabled = true;
    msgEditar.style.color = "blue";
    msgEditar.innerText = "Atualizando...";

    try {
        const resposta = await fetch(`http://127.0.0.1:5000/usuarios/${idUsuario}`, {
            method: 'PUT',
            headers: {
                "Content-Type": "application/json",
                "Authorization": "Bearer " + tokenAcesso 
            },
            body: JSON.stringify(dadosAtualizacao)
        });
        const resultado = await resposta.json();

        if(resposta.ok) {
            msgEditar.style.color = "green";
            msgEditar.textContent = resultado.mensagem;

            if(novoNome) {
                document.getElementById('nome-usuario').innerText = novoNome;
                usuarioLogado.nome = novoNome;
                localStorage.setItem('usuarioLogado', JSON.stringify(usuarioLogado))
            }

            formEditar.reset();
        } else {
            msgEditar.style.color = "red";
            msgEditar.textContent = resultado.erro;
        }
    } catch (erro) {
        msgEditar.style.color = "red";
        msgEditar.textContent = "Erro ao conectar com o servidor";
    } finally {
        btnAtualizar.disabled = false;
    }


});

const btnDeletar = document.getElementById("btn-deletar")

btnDeletar.addEventListener('click', async function() {
    const primeiraConfirmacao = confirm("Você está prestes a excluir sua conta, deseja mesmo prosseguir?");
    if (!primeiraConfirmacao) return;

    const usuarioLogado = JSON.parse(localStorage.getItem('usuarioLogado'));
    const idUsuario = usuarioLogado.id

    btnDeletar.disabled = true
    btnDeletar.textContent = "Excluindo..."

    try {
        const resposta = await fetch(`http://127.0.0.1:5000/usuarios/${idUsuario}`, {
            method: 'DELETE',
            headers: {
                "Authorization": "Bearer " + tokenAcesso
            }
        });

        const resultado = await resposta.json();

        if (resposta.ok) {
            alert(resultado.mensagem);

            fazerLogout()
        } else {
            alert("Erro ao excluir: " + resultado.erro);
            btnDeletar.disabled = false;
            btnDeletar.textContent = "Deletar Perfil";
        }
    } catch (erro) {
        alert("Erro ao conectar com o servidor.");
        btnDeletar.disabled = false;
        btnDeletar.textContent = "Excluir Minha Conta Definitivamente";
    }

});