import { SessionManager } from "./session_manager";
import { VERSION } from "./version";
import { Command } from "@commander-js/extra-typings";

const program = new Command()
    .option("-v, --visitor-data <visitordata>")
    .option("-d, --data-sync-id <data-sync-id>")
    .option("-p, --proxy <proxy-all>")
    .option("--version")
    .option("--verbose");

program.parse();
const options = program.opts();

(async () => {
    if (options.version) {
        console.log(VERSION);
        process.exit(0);
    }
    let contentBinding = options.dataSyncId || options.visitorData;
    if (options.dataSyncId) console.error("-d is deprecated, use -v instead");
    const proxy = options.proxy || "";
    const verbose = options.verbose || false;

    const sessionManager = new SessionManager(verbose);
    function log(msg: string) {
        if (verbose) console.log(msg);
    }

    if (!contentBinding)
        contentBinding =
            (await sessionManager.generateVisitorData()) || process.exit(1);
    log(`Received request for visitor data: '${contentBinding}'`);

    try {
        const sessionData = await sessionManager.generatePoToken(
            contentBinding,
            proxy,
        );
        console.log(JSON.stringify(sessionData));
    } catch (e) {
        console.error(
            `Failed while generating POT. err.name = ${e.name}. err.message = ${e.message}. err.stack = ${e.stack}`,
        );
        console.log(JSON.stringify({}));
        process.exit(1);
    }
})();
