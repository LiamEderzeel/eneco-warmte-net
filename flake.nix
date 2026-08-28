{
  description = "Dev shell for the Eneco Data Home Assistant integration";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f system);
    in
    {
      devShells = forAllSystems (system:
        let
          pkgs = import nixpkgs { inherit system; };
        in
        {
          # A venv-based shell rather than python3.withPackages: the test
          # suite depends on pytest-homeassistant-custom-component, which
          # tracks Home Assistant core's own test helpers and isn't
          # packaged in nixpkgs - pip is the only realistic way to get it.
          default = pkgs.mkShell {
            buildInputs = [
              pkgs.python3
              pkgs.python3Packages.pip
              pkgs.python3Packages.venvShellHook
            ];
            venvDir = "./.venv";
            postVenvCreation = ''
              # editable_mode=compat: HA's custom_components loader walks
              # sys.path directories directly and can't handle setuptools'
              # default PEP 660 import-hook editable install.
              pip install -e ".[test]" --config-settings editable_mode=compat
            '';
          };
        });
    };
}
